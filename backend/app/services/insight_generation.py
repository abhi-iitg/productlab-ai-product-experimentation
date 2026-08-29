"""Business logic for LLM-assisted, evidence-linked Insight generation (Stage 6).

Owns the full workflow: verify Project/Experiment ownership, verify no
Insight set has already been generated, verify analysis eligibility via
`ExperimentAnalyticsService` (including that both variants have at least
one completed run — a controlled comparison is otherwise impossible),
build the bounded deterministic context, call the Insight provider
abstraction, and persist the entire generated batch in a single
transaction. Provider and validation failures are translated into the
safe, generic exceptions in `app.core.exceptions` — no provider internals
ever reach the API boundary.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    InvalidRequestError,
    NotFoundError,
    ProviderConfigurationError,
    ProviderError,
)
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
from app.llm.insight_context import InsightContextTooLargeError, build_insight_context
from app.llm.insight_prompts import INSIGHT_PROMPT_VERSION
from app.llm.insight_provider import InsightLLMProvider
from app.models.experiment import Experiment
from app.models.insight import Insight
from app.models.project import Project
from app.models.simulation_run import SimulationRunStatus
from app.models.variant import Variant, VariantKey
from app.repositories.experiment import ExperimentRepository
from app.repositories.insight import InsightRepository
from app.repositories.project import ProjectRepository
from app.repositories.simulation_run import SimulationRunRepository
from app.services.analytics import ExperimentAnalyticsService


class InsightGenerationService:
    def __init__(self, db: Session, provider: InsightLLMProvider) -> None:
        self.db = db
        self.provider = provider
        self.projects = ProjectRepository(db)
        self.experiments = ExperimentRepository(db)
        self.runs = SimulationRunRepository(db)
        self.insights = InsightRepository(db)
        self.analytics_service = ExperimentAnalyticsService(db)

    def generate(self, project_id: int, experiment_id: int) -> list[Insight]:
        self._get_project_or_404(project_id)
        experiment = self._get_experiment_or_404(project_id, experiment_id)

        if self.insights.exists_for_experiment(experiment_id):
            raise ConflictError(f"Experiment {experiment_id} already has a generated Insight set.")

        analytics = self.analytics_service.analyze(project_id, experiment_id)
        if (
            analytics.data_quality_flags.variant_a_zero_completed_runs
            or analytics.data_quality_flags.variant_b_zero_completed_runs
        ):
            raise ConflictError(
                f"Experiment {experiment_id} has a variant with zero completed runs; "
                "a controlled comparison is not possible."
            )

        completed_runs = [
            run
            for run in self.runs.list_for_experiment(experiment_id)
            if run.status == SimulationRunStatus.COMPLETED
        ]
        variant_a, variant_b = self._ordered_variants(experiment)

        allowed_run_ids = {run.id for run in completed_runs}
        run_evidence_ids = {
            run.id: {ref["evidence_item_id"] for ref in run.evidence_references}
            for run in completed_runs
        }
        run_persona_ids = {run.id: run.persona_id for run in completed_runs}

        try:
            context = build_insight_context(
                experiment=experiment,
                variant_a=variant_a,
                variant_b=variant_b,
                analytics=analytics,
                completed_runs=completed_runs,
            )
        except InsightContextTooLargeError as exc:
            raise InvalidRequestError(str(exc)) from exc

        try:
            result = self.provider.generate_insights(
                context=context,
                allowed_run_ids=allowed_run_ids,
                run_evidence_ids=run_evidence_ids,
                run_persona_ids=run_persona_ids,
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
            raise ProviderError("The AI provider was unable to generate insights.") from exc

        insights_data = [
            {
                "category": candidate.category,
                "variant_scope": candidate.variant_scope,
                "title": candidate.title,
                "summary": candidate.summary,
                "frequency": candidate.frequency,
                "persona_count": candidate.persona_count,
                "supporting_run_ids": candidate.supporting_run_ids,
                "supporting_evidence_ids": candidate.supporting_evidence_ids,
                "confidence_level": candidate.confidence_level,
                "prompt_version": INSIGHT_PROMPT_VERSION,
                "model_name": self.provider.model_name,
            }
            for candidate in result.insights
        ]

        insights = self.insights.create_batch_for_experiment(experiment_id, insights_data)
        self._commit()
        for insight in insights:
            self.db.refresh(insight)
        return insights

    def list_for_experiment(self, project_id: int, experiment_id: int) -> list[Insight]:
        self._get_project_or_404(project_id)
        self._get_experiment_or_404(project_id, experiment_id)
        insights = self.insights.list_for_experiment(experiment_id)
        if not insights:
            raise NotFoundError(f"Experiment {experiment_id} has no generated Insight set.")
        return insights

    def _ordered_variants(self, experiment: Experiment) -> tuple[Variant, Variant]:
        by_key = {variant.key: variant for variant in experiment.variants}
        return by_key[VariantKey.A], by_key[VariantKey.B]

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
