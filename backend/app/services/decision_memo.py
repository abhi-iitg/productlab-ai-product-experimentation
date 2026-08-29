"""Business logic for structured Decision Memo generation (Stage 6).

Owns the full workflow: verify Project/Experiment ownership, require at
least one persisted Insight, recompute deterministic analytics, call the
Decision Memo provider abstraction, apply the responsible-AI decision
safety rules below, and persist exactly one memo per Experiment.

DECISION SAFETY RULES (enforced here, after schema validation, never
trusted to prompt instructions alone):

1. A `proceed` recommendation's `executive_summary` must explicitly say the
   next step is real-user validation, not launch.
2. `proceed` is rejected outright when the experiment's data-quality flags
   show a variant with zero completed runs, severe run-failure imbalance,
   or fewer than two represented personas.
3. When no completed run cites supporting evidence, the memo must include
   an uncertainty warning and must recommend collecting real evidence.
4. The memo may never claim that synthetic results prove market demand,
   product-market fit, an expected conversion rate, or launch readiness.

Any violation is treated as unusable provider output (`ProviderError`) —
the memo is not persisted.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ProviderConfigurationError,
    ProviderError,
)
from app.llm.decision_context import build_decision_context
from app.llm.decision_prompts import DECISION_PROMPT_VERSION
from app.llm.decision_provider import DecisionMemoLLMProvider
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidSchemaError,
    LLMMalformedJSONError,
    LLMProviderError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.models.decision_memo import DecisionMemo, Recommendation
from app.models.experiment import Experiment
from app.models.project import Project
from app.repositories.decision_memo import DecisionMemoRepository
from app.repositories.experiment import ExperimentRepository
from app.repositories.insight import InsightRepository
from app.repositories.project import ProjectRepository
from app.schemas.analytics import AnalyticsResponse
from app.schemas.decision_memo import DecisionMemoCandidate
from app.services.analytics import ExperimentAnalyticsService

_FORBIDDEN_MARKET_CLAIM_PHRASES = [
    "product-market fit",
    "proves market demand",
    "proven market demand",
    "validates market demand",
    "validated market demand",
    "guarantees market",
    "guaranteed market",
    "predicts market success",
    "predicted market success",
    "ready to launch",
    "ready for launch",
    "approved for launch",
    "launch readiness",
    "guaranteed conversion",
    "expected conversion rate",
]


class DecisionMemoService:
    def __init__(self, db: Session, provider: DecisionMemoLLMProvider) -> None:
        self.db = db
        self.provider = provider
        self.projects = ProjectRepository(db)
        self.experiments = ExperimentRepository(db)
        self.insights = InsightRepository(db)
        self.memos = DecisionMemoRepository(db)
        self.analytics_service = ExperimentAnalyticsService(db)

    def generate(self, project_id: int, experiment_id: int) -> DecisionMemo:
        project = self._get_project_or_404(project_id)
        experiment = self._get_experiment_or_404(project_id, experiment_id)

        if self.memos.get_for_experiment(experiment_id) is not None:
            raise ConflictError(f"Experiment {experiment_id} already has a Decision Memo.")

        insights = self.insights.list_for_experiment(experiment_id)
        if not insights:
            raise ConflictError(
                f"Experiment {experiment_id} has no generated Insights; generate "
                "Insights before requesting a decision memo."
            )

        analytics = self.analytics_service.analyze(project_id, experiment_id)

        context = build_decision_context(
            project=project, experiment=experiment, analytics=analytics, insights=insights
        )
        allowed_insight_ids = {insight.id for insight in insights}

        try:
            candidate = self.provider.generate_decision_memo(
                context=context, allowed_insight_ids=allowed_insight_ids
            )
        except LLMConfigurationError as exc:
            raise ProviderConfigurationError("The AI provider is not configured.") from exc
        except (
            LLMTimeoutError,
            LLMRateLimitError,
            LLMStatusError,
            LLMEmptyOutputError,
            LLMMalformedJSONError,
            LLMInvalidSchemaError,
            LLMProviderError,
        ) as exc:
            raise ProviderError("The AI provider was unable to generate a decision memo.") from exc

        self._apply_safety_rules(candidate, analytics)

        data = {
            "recommendation": candidate.recommendation,
            "executive_summary": candidate.executive_summary,
            "supporting_findings": candidate.supporting_findings,
            "weakest_assumptions": candidate.weakest_assumptions,
            "recommended_product_changes": candidate.recommended_product_changes,
            "risks": candidate.risks,
            "uncertain_conclusions": candidate.uncertain_conclusions,
            "recommended_success_metrics": candidate.recommended_success_metrics,
            "real_user_test": candidate.real_user_test.model_dump(),
            "supporting_insight_ids": candidate.supporting_insight_ids,
            "prompt_version": DECISION_PROMPT_VERSION,
            "model_name": self.provider.model_name,
        }
        memo = self.memos.create_for_experiment(experiment_id, data)
        self._commit()
        self.db.refresh(memo)
        return memo

    def get(self, project_id: int, experiment_id: int) -> DecisionMemo:
        self._get_project_or_404(project_id)
        self._get_experiment_or_404(project_id, experiment_id)
        memo = self.memos.get_for_experiment(experiment_id)
        if memo is None:
            raise NotFoundError(f"Experiment {experiment_id} has no Decision Memo.")
        return memo

    def _apply_safety_rules(
        self, candidate: DecisionMemoCandidate, analytics: AnalyticsResponse
    ) -> None:
        combined_text = self._collect_free_text(candidate).casefold()

        for phrase in _FORBIDDEN_MARKET_CLAIM_PHRASES:
            if phrase in combined_text:
                raise ProviderError(
                    "The AI provider response made an unsupported market-validation or "
                    "launch-readiness claim."
                )

        flags = analytics.data_quality_flags
        severe_data_quality_issue = (
            flags.variant_a_zero_completed_runs
            or flags.variant_b_zero_completed_runs
            or flags.severe_failure_imbalance
            or flags.insufficient_persona_coverage
        )
        if candidate.recommendation == Recommendation.PROCEED:
            if severe_data_quality_issue:
                raise ProviderError(
                    "The AI provider recommended proceed despite data-quality warnings "
                    "that require iterate or stop."
                )
            if "real-user validation" not in candidate.executive_summary.casefold():
                raise ProviderError(
                    "A proceed recommendation must explicitly state that the next step "
                    "is real-user validation, not launch."
                )

        if flags.no_evidence_citations:
            if not candidate.uncertain_conclusions:
                raise ProviderError(
                    "The AI provider response must include an uncertainty warning when "
                    "no completed runs cite supporting evidence."
                )
            if "evidence" not in combined_text:
                raise ProviderError(
                    "The AI provider response must recommend collecting real evidence "
                    "when no completed runs cite supporting evidence."
                )

    def _collect_free_text(self, candidate: DecisionMemoCandidate) -> str:
        test = candidate.real_user_test
        parts = [
            candidate.executive_summary,
            *candidate.supporting_findings,
            *candidate.weakest_assumptions,
            *candidate.recommended_product_changes,
            *candidate.risks,
            *candidate.uncertain_conclusions,
            *candidate.recommended_success_metrics,
            test.objective,
            test.method,
            test.sample_size_rationale,
            test.stopping_rule,
            *test.target_participants,
            *test.tasks_or_questions,
            *test.success_metrics,
        ]
        return " ".join(parts)

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    def _get_experiment_or_404(self, project_id: int, experiment_id: int) -> Experiment:
        experiment = self.experiments.get_by_project_and_id(project_id, experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found.")
        return experiment

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
