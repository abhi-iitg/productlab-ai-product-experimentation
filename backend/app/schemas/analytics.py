"""Pydantic schemas for the deterministic Experiment analytics response.

Everything here is derived purely from already-persisted, already-validated
`SimulationRun` rows — no LLM calls, no re-parsing of raw provider output.
`AnalyticsResponse` is intentionally a superset of what
`ExperimentAnalyticsService.analyze()` returns versus what the `GET
.../analysis` route exposes: `data_quality_flags` is a small set of safe,
structured booleans (never provider internals) that `InsightGenerationService`
and `DecisionMemoService` read directly to enforce eligibility and the
decision-safety rules, instead of re-deriving the same conditions from
warning text a second time.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.experiment import ExperimentStatus
from app.models.simulation_run import FailureType
from app.models.variant import VariantKey


class TaskOutcomeDistribution(BaseModel):
    completed: int
    partially_completed: int
    failed: int
    uncertain: int


class ThemeCounts(BaseModel):
    """Deterministic, verbatim counts — no clustering or semantic grouping.

    Each field is the total number of (already-normalized, per-run) entries
    of that category across every completed run for one variant.
    """

    positive_signals: int
    objections: int
    confusion_points: int
    feature_requests: int
    uncertainty_notes: int


class VariantMetrics(BaseModel):
    variant_id: int
    variant_key: VariantKey
    completed_run_count: int
    failed_run_count: int
    task_outcome_distribution: TaskOutcomeDistribution
    task_completion_rate: float | None
    average_clarity_score: float | None
    average_perceived_value_score: float | None
    average_adoption_intent_score: float | None
    average_latency_ms: float | None
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: Decimal | None


class ExperimentCoverage(BaseModel):
    expected_runs: int
    total_persisted_runs: int
    completed_runs: int
    failed_runs: int
    completion_rate: float | None
    represented_persona_count: int
    data_quality_warnings: list[str]


class EvidenceCoverage(BaseModel):
    completed_runs_with_evidence: int
    completed_runs_total: int
    evidence_citation_rate: float | None
    unique_cited_evidence_ids: list[int]


class FailureBreakdown(BaseModel):
    counts_by_category: dict[FailureType, int]
    total_failed_runs: int


class PersonaScoreProfile(BaseModel):
    average_clarity_score: float
    average_perceived_value_score: float
    average_adoption_intent_score: float


class PersonaDisagreement(BaseModel):
    persona_id: int
    variant_a_scores: PersonaScoreProfile
    variant_b_scores: PersonaScoreProfile
    direction: str
    diverges_from_overall_variant_direction: bool


class DataQualityFlags(BaseModel):
    """Safe, structured signals — never provider internals.

    `severe_failure_imbalance` is true when more than half of the
    experiment's persisted runs failed. `insufficient_persona_coverage` is
    true when fewer than two personas have a completed run.
    """

    variant_a_zero_completed_runs: bool
    variant_b_zero_completed_runs: bool
    severe_failure_imbalance: bool
    insufficient_persona_coverage: bool
    no_evidence_citations: bool


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    experiment_id: int
    experiment_status: ExperimentStatus
    coverage: ExperimentCoverage
    variant_metrics: list[VariantMetrics]
    deterministic_theme_counts: dict[VariantKey, ThemeCounts]
    failure_breakdown: FailureBreakdown
    evidence_coverage: EvidenceCoverage
    persona_disagreement: list[PersonaDisagreement]
    data_quality_warnings: list[str]
    data_quality_flags: DataQualityFlags
