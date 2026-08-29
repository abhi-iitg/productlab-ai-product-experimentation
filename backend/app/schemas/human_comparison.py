"""Pydantic schemas for the deterministic HumanFeedback-vs-synthetic
comparison response (Stage 8).

Everything here is derived purely from already-persisted, already-validated
`SimulationRun` and `HumanFeedback` rows — no LLM calls, no embeddings, no
semantic similarity, no hidden weighting formula. Theme matching is exact
(trim + collapse whitespace + case-fold) and intentionally conservative:
differently worded but related ideas are treated as distinct themes. See
`app.services.human_comparison` for the aggregation and matching logic.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.experiment import ExperimentStatus
from app.models.variant import VariantKey
from app.schemas.analytics import TaskOutcomeDistribution

MetricName = Literal["clarity", "perceived_value", "adoption_intent"]
DirectionValue = Literal["A_higher", "B_higher", "equal", "insufficient_data"]
AlignmentValue = Literal["aligned", "not_aligned", "insufficient_data"]
QualitativeCategory = Literal[
    "positive_signals", "objections", "confusion_points", "feature_requests", "uncertainty_notes"
]


class SyntheticVariantSummary(BaseModel):
    variant_key: VariantKey
    completed_run_count: int
    represented_persona_count: int
    task_outcome_distribution: TaskOutcomeDistribution
    average_clarity_score: float | None
    average_perceived_value_score: float | None
    average_adoption_intent_score: float | None
    positive_signals: list[str]
    objections: list[str]
    confusion_points: list[str]
    feature_requests: list[str]
    uncertainty_notes: list[str]


class HumanVariantSummary(BaseModel):
    variant_key: VariantKey
    feedback_record_count: int
    unique_participant_count: int
    task_outcome_distribution: TaskOutcomeDistribution
    average_clarity_score: float | None
    average_perceived_value_score: float | None
    average_adoption_intent_score: float | None
    positive_signals: list[str]
    objections: list[str]
    confusion_points: list[str]
    feature_requests: list[str]
    uncertainty_notes: list[str]


class VariantComparison(BaseModel):
    variant_key: VariantKey
    synthetic: SyntheticVariantSummary
    human: HumanVariantSummary


class VariantThemeComparison(BaseModel):
    variant_key: VariantKey
    category: QualitativeCategory
    shared_themes: list[str]
    synthetic_only_themes: list[str]
    human_only_themes: list[str]


class MetricDirectionComparison(BaseModel):
    metric: MetricName
    synthetic_direction: DirectionValue
    human_direction: DirectionValue
    alignment: AlignmentValue


class TaskOutcomeComparison(BaseModel):
    variant_key: VariantKey
    synthetic_completion_rate: float | None
    human_completion_rate: float | None
    absolute_difference: float | None


class HumanComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    experiment_id: int
    experiment_status: ExperimentStatus
    synthetic_summary: list[SyntheticVariantSummary]
    human_summary: list[HumanVariantSummary]
    variant_comparisons: list[VariantComparison]
    theme_comparisons: list[VariantThemeComparison]
    metric_direction_comparisons: list[MetricDirectionComparison]
    task_outcome_comparisons: list[TaskOutcomeComparison]
    shared_theme_count: int
    synthetic_only_theme_count: int
    human_only_theme_count: int
    data_quality_warnings: list[str]
    interpretation_notice: str
