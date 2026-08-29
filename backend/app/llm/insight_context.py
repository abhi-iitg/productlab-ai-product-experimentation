"""Deterministic Insight-generation context builder (Stage 6).

Assembles exactly what `InsightLLMProvider` implementations are allowed to
see: the experiment's objective and hypothesis, both variants' labels and
descriptions (unlike simulation context, both variants are included here —
preserving cross-variant differences is the whole point of theme
clustering), the deterministic analytics already computed by
`ExperimentAnalyticsService`, and each completed run's structured,
already-validated output (never raw provider response bodies). Evidence is
referenced only by ID and the run's own validated `supported_claims` text —
never the underlying evidence item's title or content. No web access, no
API keys, no hidden external context.

A deterministic character limit (`INSIGHT_CONTEXT_CHAR_LIMIT`) bounds the
assembled context exactly like `app.llm.context` and
`app.llm.simulation_context`: exceeding it raises
`InsightContextTooLargeError` before any provider call is made — content is
never silently truncated to fit.
"""

from app.models.experiment import Experiment
from app.models.simulation_run import SimulationRun
from app.models.variant import Variant
from app.schemas.analytics import AnalyticsResponse

# Deterministic total-content limit for the assembled Insight-generation
# context, in characters. Documented in README.md.
INSIGHT_CONTEXT_CHAR_LIMIT = 30_000


class InsightContextTooLargeError(Exception):
    """Raised when the assembled context exceeds `INSIGHT_CONTEXT_CHAR_LIMIT`.

    Raised before any provider call is made; run output content is never
    silently truncated to fit.
    """

    def __init__(self, actual_length: int, limit: int) -> None:
        self.actual_length = actual_length
        self.limit = limit
        super().__init__(
            f"Insight generation context is {actual_length} characters, exceeding the "
            f"{limit}-character limit. Reduce the number of completed runs under analysis."
        )


def _format_list(values: list[str]) -> str:
    if not values:
        return "(none recorded)"
    return "\n".join(f"- {value}" for value in values)


def _format_evidence_references(evidence_references: list[dict]) -> str:
    if not evidence_references:
        return "(none cited)"
    parts = []
    for ref in evidence_references:
        claims = "; ".join(ref["supported_claims"])
        parts.append(f"evidence_item_id={ref['evidence_item_id']} (claims: {claims})")
    return "; ".join(parts)


def _format_run(run: SimulationRun, variant_label: str) -> str:
    return (
        f"--- RUN OUTPUT START (run_id={run.id}, variant={variant_label}, "
        f"persona_id={run.persona_id}) ---\n"
        f"Task Outcome: {run.task_outcome.value}\n"
        f"Clarity: {run.clarity_score}, Perceived Value: {run.perceived_value_score}, "
        f"Adoption Intent: {run.adoption_intent_score}\n"
        f"Response Summary: {run.response_summary}\n"
        f"Positive Signals:\n{_format_list(run.positive_signals)}\n"
        f"Objections:\n{_format_list(run.objections)}\n"
        f"Confusion Points:\n{_format_list(run.confusion_points)}\n"
        f"Feature Requests:\n{_format_list(run.feature_requests)}\n"
        f"Uncertainty Notes:\n{_format_list(run.uncertainty_notes)}\n"
        f"Evidence References: {_format_evidence_references(run.evidence_references)}\n"
        f"--- RUN OUTPUT END (run_id={run.id}) ---"
    )


def format_variant_metrics_section(analytics: AnalyticsResponse) -> str:
    lines = []
    for metrics in analytics.variant_metrics:
        theme = analytics.deterministic_theme_counts[metrics.variant_key]
        lines.extend(
            [
                f"Variant {metrics.variant_key.value}:",
                f"  completed_runs={metrics.completed_run_count} "
                f"failed_runs={metrics.failed_run_count}",
                f"  task_outcome_distribution={metrics.task_outcome_distribution.model_dump()}",
                f"  task_completion_rate={metrics.task_completion_rate}",
                f"  average_clarity_score={metrics.average_clarity_score}",
                f"  average_perceived_value_score={metrics.average_perceived_value_score}",
                f"  average_adoption_intent_score={metrics.average_adoption_intent_score}",
                f"  theme_counts={theme.model_dump()}",
            ]
        )
    return "\n".join(lines)


def format_persona_disagreement_section(analytics: AnalyticsResponse) -> str:
    if not analytics.persona_disagreement:
        return "(no personas have completed runs for both variants)"
    lines = []
    for entry in analytics.persona_disagreement:
        lines.append(
            f"persona_id={entry.persona_id} direction={entry.direction} "
            f"diverges_from_overall={entry.diverges_from_overall_variant_direction} "
            f"variant_a={entry.variant_a_scores.model_dump()} "
            f"variant_b={entry.variant_b_scores.model_dump()}"
        )
    return "\n".join(lines)


def build_insight_context(
    *,
    experiment: Experiment,
    variant_a: Variant,
    variant_b: Variant,
    analytics: AnalyticsResponse,
    completed_runs: list[SimulationRun],
    char_limit: int = INSIGHT_CONTEXT_CHAR_LIMIT,
) -> str:
    """Build the deterministic context text for one Insight-generation call.

    `completed_runs` is sorted by ID regardless of input order, so the same
    persisted state always produces byte-identical context.
    """
    variant_label_by_id = {variant_a.id: "A", variant_b.id: "B"}
    ordered_runs = sorted(completed_runs, key=lambda run: run.id)
    run_ids = ", ".join(str(run.id) for run in ordered_runs)
    persona_ids = sorted({run.persona_id for run in ordered_runs})
    runs_section = "\n\n".join(
        _format_run(run, variant_label_by_id[run.variant_id]) for run in ordered_runs
    )

    sections = [
        "=== EXPERIMENT ===",
        f"Objective: {experiment.objective}",
        f"Hypothesis: {experiment.hypothesis}",
        "",
        "=== VARIANT A ===",
        f"Name: {variant_a.name}",
        f"Description: {variant_a.description}",
        "",
        "=== VARIANT B ===",
        f"Name: {variant_b.name}",
        f"Description: {variant_b.description}",
        "",
        "=== DETERMINISTIC METRICS (already computed, do not recompute) ===",
        format_variant_metrics_section(analytics),
        f"evidence_coverage={analytics.evidence_coverage.model_dump()}",
        f"failure_breakdown={analytics.failure_breakdown.counts_by_category}",
        "persona_disagreement:",
        format_persona_disagreement_section(analytics),
        f"data_quality_warnings={analytics.data_quality_warnings}",
        "",
        "=== ELIGIBLE REFERENCES ===",
        f"Allowed run_id values: {run_ids}",
        f"Persona IDs represented: {persona_ids}",
        "",
        "=== COMPLETED RUN OUTPUTS (structured, already validated) ===",
        runs_section,
        "",
        "=== GENERATION RULES ===",
        "- Only cite run_id values listed under 'Allowed run_id values' above.",
        "- Only cite evidence_item_id values that appear in a cited run's own Evidence "
        "References above.",
    ]
    context = "\n".join(sections)

    if len(context) > char_limit:
        raise InsightContextTooLargeError(len(context), char_limit)

    return context
