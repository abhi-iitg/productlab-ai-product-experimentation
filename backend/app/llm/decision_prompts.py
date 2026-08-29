"""Decision Memo prompt template and version tracking (Stage 6).

Prompt text lives here, never inside route functions or the service layer.
`DECISION_PROMPT_VERSION` is persisted on every generated memo for
reproducibility — bump it whenever the instructions below change materially.

Decision *safety* rules (severe data-quality warnings blocking Proceed,
forbidden market/launch-validation language) are re-enforced in
`app.services.decision_memo` after the provider responds — a model is
instructed to follow these rules, but instructions alone are never trusted
as the sole safeguard.
"""

DECISION_PROMPT_VERSION = "decision-v1"

_RESPONSE_SHAPE = (
    "{"
    '"recommendation": "proceed" | "iterate" | "stop", '
    '"executive_summary": str, '
    '"supporting_findings": [str], "weakest_assumptions": [str], '
    '"recommended_product_changes": [str], "risks": [str], '
    '"uncertain_conclusions": [str], "recommended_success_metrics": [str], '
    '"real_user_test": {'
    '"objective": str, "target_participants": [str], "method": str, '
    '"sample_size_rationale": str, "tasks_or_questions": [str], '
    '"success_metrics": [str], "stopping_rule": str'
    "}, "
    '"supporting_insight_ids": [int]'
    "}"
)


def build_decision_system_instructions() -> str:
    """Stable system/developer instructions for a Decision Memo generation call."""
    return (
        "You are a product research analyst producing a structured Proceed/Iterate/Stop "
        "decision memo from a set of already-persisted, evidence-linked Insights, for "
        "hypothesis generation and experiment planning — not a market-validation "
        "verdict. Rules:\n"
        "1. Select exactly one recommendation — proceed, iterate, or stop — using the "
        "exact meanings supplied under 'RESPONSIBLE-AI DECISION DEFINITIONS'. A "
        "'proceed' recommendation must explicitly state in executive_summary that the "
        "next step is real-user validation, not launch — include the phrase "
        "'real-user validation' in executive_summary whenever you select proceed.\n"
        "2. Ground supporting_findings, weakest_assumptions, risks, and "
        "uncertain_conclusions in the supplied Insights and deterministic metrics only. "
        "Cite only insight_id values listed under 'Allowed insight_id values'; never "
        "invent or reference any other insight_id.\n"
        "3. If data_quality_warnings indicate a variant with zero completed runs, "
        "severe run-failure imbalance, or fewer than two represented personas, do not "
        "recommend proceed — recommend iterate or stop instead.\n"
        "4. If no completed run cites supporting evidence, add an explicit item under "
        "uncertain_conclusions noting the absence of evidence citations, and ensure "
        "recommended_product_changes or real_user_test.objective calls for collecting "
        "real evidence before further investment.\n"
        "5. Never state or imply that these synthetic results prove market demand, "
        "product-market fit, an expected conversion rate, or launch readiness. Never "
        "recommend launching a product based only on synthetic feedback. Synthetic "
        "feedback supports hypothesis generation and experiment planning only — it "
        "does not replace real-user research or predict market success.\n"
        "6. real_user_test.sample_size_rationale must explain why the proposed scope "
        "is appropriate for the next learning step — never claim a specific "
        "participant count alone guarantees statistical validity.\n"
        "7. Every list field must contain at least one specific, non-generic item "
        "grounded in the supplied Insights or metrics.\n"
        "8. Return ONLY a single JSON object matching this shape, with no extra "
        f"commentary or markdown formatting: {_RESPONSE_SHAPE}"
    )


def build_decision_user_prompt(context: str) -> str:
    """The user prompt for a Decision Memo generation call: the deterministic context, unchanged."""
    return context
