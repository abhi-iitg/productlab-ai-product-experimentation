"""Deterministic analytics aggregation over persisted SimulationRuns (Stage 6).

`ExperimentAnalyticsService` makes no LLM calls and no database writes — it
only reads already-persisted, already-validated `SimulationRun` rows and
aggregates them. No embeddings, semantic similarity, external analytics
services, or hidden weighting formulas: every number here is a plain count,
sum, or mean over explicit fields, and is reproducible from the persisted
rows alone.

Analysis is only available once an Experiment has left `draft`/`running`
and has at least one completed run (see `_require_eligible`); callers that
need a stricter guarantee (a real two-variant comparison) additionally
check `AnalyticsResponse.data_quality_flags` — e.g.
`InsightGenerationService` rejects generation outright when either variant
has zero completed runs, since no controlled comparison is possible.
"""

from decimal import Decimal
from statistics import mean

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.experiment import Experiment, ExperimentStatus
from app.models.project import Project
from app.models.simulation_run import FailureType, SimulationRun, SimulationRunStatus, TaskOutcome
from app.models.variant import Variant, VariantKey
from app.repositories.experiment import ExperimentRepository
from app.repositories.project import ProjectRepository
from app.repositories.simulation_run import SimulationRunRepository
from app.schemas.analytics import (
    AnalyticsResponse,
    DataQualityFlags,
    EvidenceCoverage,
    ExperimentCoverage,
    FailureBreakdown,
    PersonaDisagreement,
    PersonaScoreProfile,
    TaskOutcomeDistribution,
    ThemeCounts,
    VariantMetrics,
)

_VARIANT_COUNT = 2
_SEVERE_FAILURE_RATE_THRESHOLD = 0.5
_MIN_REPRESENTED_PERSONAS = 2
_ROUND_DIGITS = 4

_ELIGIBLE_STATUSES = {ExperimentStatus.COMPLETED, ExperimentStatus.PARTIALLY_COMPLETED}


def _round(value: float) -> float:
    return round(value, _ROUND_DIGITS)


def _mean_score(values: list[int]) -> float | None:
    if not values:
        return None
    return _round(mean(values))


class ExperimentAnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.experiments = ExperimentRepository(db)
        self.runs = SimulationRunRepository(db)

    def analyze(self, project_id: int, experiment_id: int) -> AnalyticsResponse:
        self._get_project_or_404(project_id)
        experiment = self._get_experiment_or_404(project_id, experiment_id)

        all_runs = self.runs.list_for_experiment(experiment_id)
        completed_runs = [r for r in all_runs if r.status == SimulationRunStatus.COMPLETED]
        failed_runs = [r for r in all_runs if r.status == SimulationRunStatus.FAILED]

        self._require_eligible(experiment, completed_runs)

        variant_a, variant_b = self._ordered_variants(experiment)
        coverage, flags, warnings = self._build_coverage(
            experiment, all_runs, completed_runs, failed_runs, variant_a, variant_b
        )

        variant_metrics = [
            self._variant_metrics(variant, all_runs) for variant in (variant_a, variant_b)
        ]
        theme_counts = {
            variant.key: self._theme_counts(variant, completed_runs)
            for variant in (variant_a, variant_b)
        }
        failure_breakdown = self._failure_breakdown(failed_runs)
        evidence_coverage = self._evidence_coverage(completed_runs)
        persona_disagreement = self._persona_disagreement(
            completed_runs, variant_a, variant_b, variant_metrics
        )

        return AnalyticsResponse(
            experiment_id=experiment_id,
            experiment_status=experiment.status,
            coverage=coverage,
            variant_metrics=variant_metrics,
            deterministic_theme_counts=theme_counts,
            failure_breakdown=failure_breakdown,
            evidence_coverage=evidence_coverage,
            persona_disagreement=persona_disagreement,
            data_quality_warnings=warnings,
            data_quality_flags=flags,
        )

    def _require_eligible(
        self, experiment: Experiment, completed_runs: list[SimulationRun]
    ) -> None:
        if experiment.status not in _ELIGIBLE_STATUSES:
            raise ConflictError(
                f"Experiment {experiment.id} must be completed or partially_completed "
                "before analysis is available."
            )
        if not completed_runs:
            raise ConflictError(
                f"Experiment {experiment.id} has zero completed runs; analysis is not available."
            )

    def _ordered_variants(self, experiment: Experiment) -> tuple[Variant, Variant]:
        by_key = {variant.key: variant for variant in experiment.variants}
        return by_key[VariantKey.A], by_key[VariantKey.B]

    def _build_coverage(
        self,
        experiment: Experiment,
        all_runs: list[SimulationRun],
        completed_runs: list[SimulationRun],
        failed_runs: list[SimulationRun],
        variant_a: Variant,
        variant_b: Variant,
    ) -> tuple[ExperimentCoverage, DataQualityFlags, list[str]]:
        persona_ids = self.experiments.get_persona_ids(experiment.id)
        expected_runs = len(persona_ids) * _VARIANT_COUNT * experiment.repeat_count
        total_persisted_runs = len(all_runs)
        completed_count = len(completed_runs)
        failed_count = len(failed_runs)
        completion_rate = _round(completed_count / expected_runs) if expected_runs > 0 else None
        represented_persona_ids = {run.persona_id for run in completed_runs}

        variant_a_completed = any(run.variant_id == variant_a.id for run in completed_runs)
        variant_b_completed = any(run.variant_id == variant_b.id for run in completed_runs)
        severe_failure_imbalance = (
            total_persisted_runs > 0
            and (failed_count / total_persisted_runs) >= _SEVERE_FAILURE_RATE_THRESHOLD
        )
        insufficient_persona_coverage = len(represented_persona_ids) < _MIN_REPRESENTED_PERSONAS
        no_evidence_citations = not any(run.evidence_references for run in completed_runs)

        flags = DataQualityFlags(
            variant_a_zero_completed_runs=not variant_a_completed,
            variant_b_zero_completed_runs=not variant_b_completed,
            severe_failure_imbalance=severe_failure_imbalance,
            insufficient_persona_coverage=insufficient_persona_coverage,
            no_evidence_citations=no_evidence_citations,
        )
        warnings = self._build_warnings(flags)

        coverage = ExperimentCoverage(
            expected_runs=expected_runs,
            total_persisted_runs=total_persisted_runs,
            completed_runs=completed_count,
            failed_runs=failed_count,
            completion_rate=completion_rate,
            represented_persona_count=len(represented_persona_ids),
            data_quality_warnings=warnings,
        )
        return coverage, flags, warnings

    def _build_warnings(self, flags: DataQualityFlags) -> list[str]:
        warnings: list[str] = []
        if flags.variant_a_zero_completed_runs:
            warnings.append(
                "Variant A has zero completed runs; a controlled comparison between "
                "variants is not possible."
            )
        if flags.variant_b_zero_completed_runs:
            warnings.append(
                "Variant B has zero completed runs; a controlled comparison between "
                "variants is not possible."
            )
        if flags.severe_failure_imbalance:
            warnings.append(
                "More than half of persisted runs failed; treat these results with caution."
            )
        if flags.insufficient_persona_coverage:
            warnings.append(
                "Fewer than two personas have completed runs; persona-level comparison is limited."
            )
        if flags.no_evidence_citations:
            warnings.append(
                "No completed runs cite supporting evidence; treat qualitative findings "
                "as unsupported until evidence coverage improves."
            )
        return warnings

    def _variant_metrics(self, variant: Variant, all_runs: list[SimulationRun]) -> VariantMetrics:
        variant_runs = [run for run in all_runs if run.variant_id == variant.id]
        completed = [run for run in variant_runs if run.status == SimulationRunStatus.COMPLETED]
        failed = [run for run in variant_runs if run.status == SimulationRunStatus.FAILED]

        distribution_counts = {outcome: 0 for outcome in TaskOutcome}
        for run in completed:
            distribution_counts[run.task_outcome] += 1
        distribution = TaskOutcomeDistribution(
            completed=distribution_counts[TaskOutcome.COMPLETED],
            partially_completed=distribution_counts[TaskOutcome.PARTIALLY_COMPLETED],
            failed=distribution_counts[TaskOutcome.FAILED],
            uncertain=distribution_counts[TaskOutcome.UNCERTAIN],
        )
        task_completion_rate = (
            _round(distribution.completed / len(completed)) if completed else None
        )

        latencies = [run.latency_ms for run in completed if run.latency_ms is not None]
        total_input_tokens = sum(run.input_tokens or 0 for run in completed)
        total_output_tokens = sum(run.output_tokens or 0 for run in completed)
        total_cost = (
            sum((run.estimated_cost_usd for run in completed), Decimal("0"))
            if all(run.estimated_cost_usd is not None for run in completed)
            else None
        )

        return VariantMetrics(
            variant_id=variant.id,
            variant_key=variant.key,
            completed_run_count=len(completed),
            failed_run_count=len(failed),
            task_outcome_distribution=distribution,
            task_completion_rate=task_completion_rate,
            average_clarity_score=_mean_score([run.clarity_score for run in completed]),
            average_perceived_value_score=_mean_score(
                [run.perceived_value_score for run in completed]
            ),
            average_adoption_intent_score=_mean_score(
                [run.adoption_intent_score for run in completed]
            ),
            average_latency_ms=_round(mean(latencies)) if latencies else None,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_estimated_cost_usd=total_cost,
        )

    def _theme_counts(self, variant: Variant, completed_runs: list[SimulationRun]) -> ThemeCounts:
        variant_completed = [run for run in completed_runs if run.variant_id == variant.id]
        return ThemeCounts(
            positive_signals=sum(len(run.positive_signals) for run in variant_completed),
            objections=sum(len(run.objections) for run in variant_completed),
            confusion_points=sum(len(run.confusion_points) for run in variant_completed),
            feature_requests=sum(len(run.feature_requests) for run in variant_completed),
            uncertainty_notes=sum(len(run.uncertainty_notes) for run in variant_completed),
        )

    def _failure_breakdown(self, failed_runs: list[SimulationRun]) -> FailureBreakdown:
        counts = {failure_type: 0 for failure_type in FailureType}
        for run in failed_runs:
            if run.failure_type is not None:
                counts[run.failure_type] += 1
        return FailureBreakdown(counts_by_category=counts, total_failed_runs=len(failed_runs))

    def _evidence_coverage(self, completed_runs: list[SimulationRun]) -> EvidenceCoverage:
        with_evidence = [run for run in completed_runs if run.evidence_references]
        cited_ids: set[int] = set()
        for run in completed_runs:
            cited_ids.update(ref["evidence_item_id"] for ref in run.evidence_references)
        rate = _round(len(with_evidence) / len(completed_runs)) if completed_runs else None
        return EvidenceCoverage(
            completed_runs_with_evidence=len(with_evidence),
            completed_runs_total=len(completed_runs),
            evidence_citation_rate=rate,
            unique_cited_evidence_ids=sorted(cited_ids),
        )

    def _persona_disagreement(
        self,
        completed_runs: list[SimulationRun],
        variant_a: Variant,
        variant_b: Variant,
        variant_metrics: list[VariantMetrics],
    ) -> list[PersonaDisagreement]:
        by_persona_variant: dict[tuple[int, int], list[SimulationRun]] = {}
        for run in completed_runs:
            by_persona_variant.setdefault((run.persona_id, run.variant_id), []).append(run)

        persona_ids = {run.persona_id for run in completed_runs}
        overall_direction = self._direction_from_scores(
            self._overall_score(variant_metrics[0]), self._overall_score(variant_metrics[1])
        )

        results: list[PersonaDisagreement] = []
        for persona_id in sorted(persona_ids):
            a_runs = by_persona_variant.get((persona_id, variant_a.id))
            b_runs = by_persona_variant.get((persona_id, variant_b.id))
            if not a_runs or not b_runs:
                continue

            a_profile = self._score_profile(a_runs)
            b_profile = self._score_profile(b_runs)
            direction = self._direction_from_scores(
                self._profile_overall(a_profile), self._profile_overall(b_profile)
            )
            results.append(
                PersonaDisagreement(
                    persona_id=persona_id,
                    variant_a_scores=a_profile,
                    variant_b_scores=b_profile,
                    direction=direction,
                    diverges_from_overall_variant_direction=direction != overall_direction,
                )
            )
        return results

    def _score_profile(self, runs: list[SimulationRun]) -> PersonaScoreProfile:
        return PersonaScoreProfile(
            average_clarity_score=_round(mean(run.clarity_score for run in runs)),
            average_perceived_value_score=_round(mean(run.perceived_value_score for run in runs)),
            average_adoption_intent_score=_round(mean(run.adoption_intent_score for run in runs)),
        )

    def _profile_overall(self, profile: PersonaScoreProfile) -> float:
        return mean(
            [
                profile.average_clarity_score,
                profile.average_perceived_value_score,
                profile.average_adoption_intent_score,
            ]
        )

    def _overall_score(self, metrics: VariantMetrics) -> float | None:
        scores = [
            score
            for score in (
                metrics.average_clarity_score,
                metrics.average_perceived_value_score,
                metrics.average_adoption_intent_score,
            )
            if score is not None
        ]
        return mean(scores) if scores else None

    def _direction_from_scores(self, score_a: float | None, score_b: float | None) -> str:
        if score_a is None or score_b is None:
            return "neutral"
        if score_a > score_b:
            return "prefers_a"
        if score_b > score_a:
            return "prefers_b"
        return "neutral"

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
