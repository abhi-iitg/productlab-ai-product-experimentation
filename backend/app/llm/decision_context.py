"""Deterministic Decision Memo context builder (Stage 6).

Assembles exactly what `DecisionMemoLLMProvider` implementations are
allowed to see: the experiment's objective, hypothesis, and the project's
stated success metric, the deterministic analytics already computed by
`ExperimentAnalyticsService`, every persisted `Insight` for the experiment
(already-distilled, already-validated — never raw run output or evidence
content), the analytics data-quality warnings, and the exact
responsible-AI Proceed/Iterate/Stop definitions the provider must use. No
web access, no API keys, no hidden external context.

Unlike Insight generation, no separate character limit is enforced here:
the context is built from at most 12 persisted Insights plus a short
deterministic analytics summary, which is inherently small and bounded by
`INSIGHT_CONTEXT_CHAR_LIMIT` having already bounded the run data that
produced those Insights.
"""

from app.llm.insight_context import (
    format_persona_disagreement_section,
    format_variant_metrics_section,
)
from app.models.experiment import Experiment
from app.models.insight import Insight
from app.models.project import Project
from app.schemas.analytics import AnalyticsResponse

_DECISION_DEFINITIONS = (
    "- Proceed: The current concept or variant has enough synthetic signal to justify "
    "moving into real-user validation. It does not mean launch.\n"
    "- Iterate: Important assumptions, confusion, objections, or evidence gaps should "
    "be addressed before real-user validation.\n"
    "- Stop: The current concept or hypothesis should not receive further investment "
    "in its present form. This does not prove that the broader market opportunity is "
    "invalid."
)

_RESPONSIBLE_AI_NOTICE = (
    "Synthetic feedback supports hypothesis generation and experiment planning. It "
    "does not replace real-user research or predict market success."
)


def _format_insight(insight: Insight) -> str:
    return (
        f"--- INSIGHT START (insight_id={insight.id}) ---\n"
        f"Category: {insight.category.value}\n"
        f"Variant Scope: {insight.variant_scope.value}\n"
        f"Title: {insight.title}\n"
        f"Summary: {insight.summary}\n"
        f"Frequency: {insight.frequency}\n"
        f"Persona Count: {insight.persona_count}\n"
        f"Confidence Level: {insight.confidence_level.value}\n"
        f"--- INSIGHT END (insight_id={insight.id}) ---"
    )


def build_decision_context(
    *,
    project: Project,
    experiment: Experiment,
    analytics: AnalyticsResponse,
    insights: list[Insight],
) -> str:
    """Build the deterministic context text for one Decision Memo generation call.

    `insights` is sorted by ID regardless of input order, so the same
    persisted state always produces byte-identical context.
    """
    ordered_insights = sorted(insights, key=lambda insight: insight.id)
    insight_ids = ", ".join(str(insight.id) for insight in ordered_insights)
    insights_section = "\n\n".join(_format_insight(insight) for insight in ordered_insights)

    sections = [
        "=== EXPERIMENT ===",
        f"Objective: {experiment.objective}",
        f"Hypothesis: {experiment.hypothesis}",
        f"Product Success Metric: {project.success_metric}",
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
        f"Allowed insight_id values: {insight_ids}",
        "",
        "=== PERSISTED INSIGHTS (structured, already validated) ===",
        insights_section,
        "",
        "=== RESPONSIBLE-AI DECISION DEFINITIONS (use exactly these meanings) ===",
        _DECISION_DEFINITIONS,
        _RESPONSIBLE_AI_NOTICE,
        "",
        "=== GENERATION RULES ===",
        "- Only cite insight_id values listed under 'Allowed insight_id values' above.",
    ]
    return "\n".join(sections)
