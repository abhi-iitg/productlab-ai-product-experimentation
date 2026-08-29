"""Deterministic comparison of persisted SimulationRuns against manually
entered HumanFeedback (Stage 8).

`HumanComparisonService` makes no LLM calls, no embeddings calls, and no
database writes — it only reads already-persisted, already-validated
`SimulationRun` and `HumanFeedback` rows and aggregates/compares them.
Qualitative theme matching is exact (trim + collapse internal whitespace +
case-fold): differently worded but related ideas are intentionally treated
as distinct themes rather than fuzzily merged. Every number here is a
plain count, sum, or mean over explicit fields, reproducible from the
persisted rows alone. `ExperimentAnalyticsService` is not imported here on
purpose — the two deterministic services stay decoupled and each recomputes
its own eligibility conditions independently.
"""

from collections.abc import Iterable
from statistics import mean

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.experiment import Experiment, ExperimentStatus
from app.models.human_feedback import HumanFeedback
from app.models.project import Project
from app.models.simulation_run import SimulationRun, SimulationRunStatus, TaskOutcome
from app.models.variant import Variant, VariantKey
from app.repositories.decision_memo import DecisionMemoRepository
from app.repositories.experiment import ExperimentRepository
from app.repositories.human_feedback import HumanFeedbackRepository
from app.repositories.project import ProjectRepository
from app.repositories.simulation_run import SimulationRunRepository
from app.schemas.analytics import TaskOutcomeDistribution
from app.schemas.human_comparison import (
    HumanComparisonResponse,
    HumanVariantSummary,
    MetricDirectionComparison,
    SyntheticVariantSummary,
    TaskOutcomeComparison,
    VariantComparison,
    VariantThemeComparison,
)

_ELIGIBLE_STATUSES = {ExperimentStatus.COMPLETED, ExperimentStatus.PARTIALLY_COMPLETED}
_ROUND_DIGITS = 4
_SEVERE_IMBALANCE_RATIO = 3
_QUALITATIVE_FIELDS = (
    "positive_signals",
    "objections",
    "confusion_points",
    "feature_requests",
    "uncertainty_notes",
)

INTERPRETATION_NOTICE = (
    "The comparison highlights agreement and gaps between synthetic simulations "
    "and a manually entered qualitative sample. It does not establish statistical "
    "significance, predictive validity, or market demand."
)

_EXACT_MATCH_LIMITATION_WARNING = (
    "Theme matching is exact (trimmed, whitespace-collapsed, case-insensitive) "
    "and intentionally conservative — differently worded but related ideas are "
    "treated as distinct themes rather than merged."
)

_PII_REMINDER_WARNING = (
    "Real-participant feedback fields are free text. This platform does not "
    "automatically detect personally identifiable information — review entries "
    "for PII before sharing this comparison if the anonymization notice may not "
    "have been followed."
)


def _round(value: float) -> float:
    return round(value, _ROUND_DIGITS)


def _mean_score(values: list[int]) -> float | None:
    if not values:
        return None
    return _round(mean(values))


def _normalize_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _aggregate_qualitative(raw_values: Iterable[str]) -> list[str]:
    """Trim, collapse internal whitespace, and dedupe case-insensitively
    across rows, keeping the first-seen collapsed display casing. Exact
    matching only — no fuzzy matching, embeddings, or LLM clustering."""
    seen: dict[str, str] = {}
    for raw in raw_values:
        collapsed = " ".join(raw.split())
        if not collapsed:
            continue
        key = _normalize_key(collapsed)
        if key not in seen:
            seen[key] = collapsed
    return sorted(seen.values(), key=str.casefold)


def _direction(score_a: float | None, score_b: float | None) -> str:
    if score_a is None or score_b is None:
        return "insufficient_data"
    if score_a > score_b:
        return "A_higher"
    if score_b > score_a:
        return "B_higher"
    return "equal"


def _task_outcome_distribution(outcomes: Iterable[TaskOutcome]) -> TaskOutcomeDistribution:
    counts = {outcome: 0 for outcome in TaskOutcome}
    for outcome in outcomes:
        counts[outcome] += 1
    return TaskOutcomeDistribution(
        completed=counts[TaskOutcome.COMPLETED],
        partially_completed=counts[TaskOutcome.PARTIALLY_COMPLETED],
        failed=counts[TaskOutcome.FAILED],
        uncertain=counts[TaskOutcome.UNCERTAIN],
    )


class HumanComparisonService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.experiments = ExperimentRepository(db)
        self.runs = SimulationRunRepository(db)
        self.feedback = HumanFeedbackRepository(db)
        self.decision_memos = DecisionMemoRepository(db)

    def compare(self, project_id: int, experiment_id: int) -> HumanComparisonResponse:
        self._get_project_or_404(project_id)
        experiment = self._get_experiment_or_404(project_id, experiment_id)

        if experiment.status not in _ELIGIBLE_STATUSES:
            raise ConflictError(
                f"Experiment {experiment_id} must be completed or partially_completed "
                "before a real-vs-synthetic comparison is available."
            )

        all_runs = self.runs.list_for_experiment(experiment_id)
        completed_runs = [run for run in all_runs if run.status == SimulationRunStatus.COMPLETED]
        if not completed_runs:
            raise ConflictError(
                f"Experiment {experiment_id} has zero completed synthetic runs; there is no "
                "synthetic baseline to compare against."
            )

        feedback_records = self.feedback.list_for_experiment(experiment_id)
        variant_a, variant_b = self._ordered_variants(experiment)

        synthetic_summary = [
            self._synthetic_summary(variant, completed_runs) for variant in (variant_a, variant_b)
        ]
        human_summary = [
            self._human_summary(variant, feedback_records) for variant in (variant_a, variant_b)
        ]
        variant_comparisons = [
            VariantComparison(variant_key=syn.variant_key, synthetic=syn, human=hum)
            for syn, hum in zip(synthetic_summary, human_summary, strict=True)
        ]

        theme_comparisons = self._theme_comparisons(synthetic_summary, human_summary)
        metric_direction_comparisons = self._metric_direction_comparisons(
            synthetic_summary, human_summary
        )
        task_outcome_comparisons = self._task_outcome_comparisons(synthetic_summary, human_summary)

        shared_theme_count = sum(len(t.shared_themes) for t in theme_comparisons)
        synthetic_only_theme_count = sum(len(t.synthetic_only_themes) for t in theme_comparisons)
        human_only_theme_count = sum(len(t.human_only_themes) for t in theme_comparisons)

        warnings = self._data_quality_warnings(
            experiment_id=experiment_id,
            feedback_records=feedback_records,
            synthetic_summary=synthetic_summary,
            human_summary=human_summary,
            shared_theme_count=shared_theme_count,
        )

        return HumanComparisonResponse(
            project_id=project_id,
            experiment_id=experiment_id,
            experiment_status=experiment.status,
            synthetic_summary=synthetic_summary,
            human_summary=human_summary,
            variant_comparisons=variant_comparisons,
            theme_comparisons=theme_comparisons,
            metric_direction_comparisons=metric_direction_comparisons,
            task_outcome_comparisons=task_outcome_comparisons,
            shared_theme_count=shared_theme_count,
            synthetic_only_theme_count=synthetic_only_theme_count,
            human_only_theme_count=human_only_theme_count,
            data_quality_warnings=warnings,
            interpretation_notice=INTERPRETATION_NOTICE,
        )

    def _ordered_variants(self, experiment: Experiment) -> tuple[Variant, Variant]:
        by_key = {variant.key: variant for variant in experiment.variants}
        return by_key[VariantKey.A], by_key[VariantKey.B]

    def _synthetic_summary(
        self, variant: Variant, completed_runs: list[SimulationRun]
    ) -> SyntheticVariantSummary:
        runs = [run for run in completed_runs if run.variant_id == variant.id]
        return SyntheticVariantSummary(
            variant_key=variant.key,
            completed_run_count=len(runs),
            represented_persona_count=len({run.persona_id for run in runs}),
            task_outcome_distribution=_task_outcome_distribution(run.task_outcome for run in runs),
            average_clarity_score=_mean_score([run.clarity_score for run in runs]),
            average_perceived_value_score=_mean_score([run.perceived_value_score for run in runs]),
            average_adoption_intent_score=_mean_score([run.adoption_intent_score for run in runs]),
            **{
                field: _aggregate_qualitative(
                    value for run in runs for value in getattr(run, field)
                )
                for field in _QUALITATIVE_FIELDS
            },
        )

    def _human_summary(
        self, variant: Variant, feedback_records: list[HumanFeedback]
    ) -> HumanVariantSummary:
        records = [f for f in feedback_records if f.variant_key == variant.key]
        return HumanVariantSummary(
            variant_key=variant.key,
            feedback_record_count=len(records),
            unique_participant_count=len({f.participant_label for f in records}),
            task_outcome_distribution=_task_outcome_distribution(f.task_outcome for f in records),
            average_clarity_score=_mean_score([f.clarity_score for f in records]),
            average_perceived_value_score=_mean_score([f.perceived_value_score for f in records]),
            average_adoption_intent_score=_mean_score([f.adoption_intent_score for f in records]),
            **{
                field: _aggregate_qualitative(value for f in records for value in getattr(f, field))
                for field in _QUALITATIVE_FIELDS
            },
        )

    def _theme_comparisons(
        self,
        synthetic_summary: list[SyntheticVariantSummary],
        human_summary: list[HumanVariantSummary],
    ) -> list[VariantThemeComparison]:
        comparisons: list[VariantThemeComparison] = []
        for syn, hum in zip(synthetic_summary, human_summary, strict=True):
            for field in _QUALITATIVE_FIELDS:
                syn_map = {_normalize_key(v): v for v in getattr(syn, field)}
                hum_map = {_normalize_key(v): v for v in getattr(hum, field)}
                shared_keys = sorted(syn_map.keys() & hum_map.keys())
                synthetic_only_keys = sorted(syn_map.keys() - hum_map.keys())
                human_only_keys = sorted(hum_map.keys() - syn_map.keys())
                comparisons.append(
                    VariantThemeComparison(
                        variant_key=syn.variant_key,
                        category=field,
                        shared_themes=[syn_map[k] for k in shared_keys],
                        synthetic_only_themes=[syn_map[k] for k in synthetic_only_keys],
                        human_only_themes=[hum_map[k] for k in human_only_keys],
                    )
                )
        return comparisons

    def _metric_direction_comparisons(
        self,
        synthetic_summary: list[SyntheticVariantSummary],
        human_summary: list[HumanVariantSummary],
    ) -> list[MetricDirectionComparison]:
        syn_a, syn_b = synthetic_summary
        hum_a, hum_b = human_summary
        metrics: list[tuple[str, float | None, float | None, float | None, float | None]] = [
            (
                "clarity",
                syn_a.average_clarity_score,
                syn_b.average_clarity_score,
                hum_a.average_clarity_score,
                hum_b.average_clarity_score,
            ),
            (
                "perceived_value",
                syn_a.average_perceived_value_score,
                syn_b.average_perceived_value_score,
                hum_a.average_perceived_value_score,
                hum_b.average_perceived_value_score,
            ),
            (
                "adoption_intent",
                syn_a.average_adoption_intent_score,
                syn_b.average_adoption_intent_score,
                hum_a.average_adoption_intent_score,
                hum_b.average_adoption_intent_score,
            ),
        ]
        comparisons = []
        for metric, syn_score_a, syn_score_b, hum_score_a, hum_score_b in metrics:
            synthetic_direction = _direction(syn_score_a, syn_score_b)
            human_direction = _direction(hum_score_a, hum_score_b)
            if "insufficient_data" in (synthetic_direction, human_direction):
                alignment = "insufficient_data"
            elif synthetic_direction == human_direction:
                alignment = "aligned"
            else:
                alignment = "not_aligned"
            comparisons.append(
                MetricDirectionComparison(
                    metric=metric,
                    synthetic_direction=synthetic_direction,
                    human_direction=human_direction,
                    alignment=alignment,
                )
            )
        return comparisons

    def _task_outcome_comparisons(
        self,
        synthetic_summary: list[SyntheticVariantSummary],
        human_summary: list[HumanVariantSummary],
    ) -> list[TaskOutcomeComparison]:
        comparisons = []
        for syn, hum in zip(synthetic_summary, human_summary, strict=True):
            synthetic_rate = (
                _round(syn.task_outcome_distribution.completed / syn.completed_run_count)
                if syn.completed_run_count > 0
                else None
            )
            human_rate = (
                _round(hum.task_outcome_distribution.completed / hum.feedback_record_count)
                if hum.feedback_record_count > 0
                else None
            )
            absolute_difference = (
                _round(abs(synthetic_rate - human_rate))
                if synthetic_rate is not None and human_rate is not None
                else None
            )
            comparisons.append(
                TaskOutcomeComparison(
                    variant_key=syn.variant_key,
                    synthetic_completion_rate=synthetic_rate,
                    human_completion_rate=human_rate,
                    absolute_difference=absolute_difference,
                )
            )
        return comparisons

    def _data_quality_warnings(
        self,
        *,
        experiment_id: int,
        feedback_records: list[HumanFeedback],
        synthetic_summary: list[SyntheticVariantSummary],
        human_summary: list[HumanVariantSummary],
        shared_theme_count: int,
    ) -> list[str]:
        warnings: list[str] = []

        if not feedback_records:
            warnings.append(
                "No real-participant feedback has been entered yet; this comparison reflects "
                "synthetic results only. Add human feedback to compare it against the synthetic "
                "findings."
            )
        else:
            # Small-sample severity tiers are mutually exclusive (one participant vs.
            # fewer-than-three) to avoid stacking redundant warnings for the same
            # underlying condition.
            distinct_participants = {f.participant_label for f in feedback_records}
            if len(distinct_participants) == 1:
                warnings.append(
                    "Only one real participant has provided feedback; treat this as a single "
                    "qualitative data point, not a representative sample."
                )
            elif len(distinct_participants) == 2:
                warnings.append(
                    "Fewer than three real participants have provided feedback; treat this as "
                    "a small qualitative sample, not a representative sample."
                )

        for hum in human_summary:
            other = next(h for h in human_summary if h is not hum)
            if hum.feedback_record_count == 0 and other.feedback_record_count > 0:
                warnings.append(
                    f"Variant {hum.variant_key.value} has no real-participant feedback; a "
                    "real-vs-synthetic comparison for this variant is not possible."
                )

        counts = [hum.feedback_record_count for hum in human_summary]
        if all(c > 0 for c in counts) and max(counts) / min(counts) >= _SEVERE_IMBALANCE_RATIO:
            warnings.append(
                "Real-participant sample sizes are severely imbalanced between variants; "
                "treat cross-variant comparisons with caution."
            )

        for syn in synthetic_summary:
            if syn.completed_run_count == 0:
                warnings.append(
                    f"Variant {syn.variant_key.value} has zero completed synthetic runs; a "
                    "controlled comparison for this variant is not possible."
                )

        if shared_theme_count == 0 and any(
            getattr(syn, field) or getattr(hum, field)
            for syn, hum in zip(synthetic_summary, human_summary, strict=True)
            for field in _QUALITATIVE_FIELDS
        ):
            warnings.append(
                "No exactly matching themes were found between synthetic and real-participant "
                "feedback."
            )

        warnings.append(_EXACT_MATCH_LIMITATION_WARNING)

        memo = self.decision_memos.get_for_experiment(experiment_id)
        if memo is not None and feedback_records:
            latest_feedback_at = max(f.created_at for f in feedback_records)
            if memo.created_at < latest_feedback_at:
                warnings.append(
                    "The existing Decision Memo predates some or all of this real-participant "
                    "feedback and was not automatically regenerated to reflect it."
                )

        if feedback_records:
            warnings.append(_PII_REMINDER_WARNING)

        return warnings

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
