"""Insight-generation prompt template and version tracking (Stage 6).

Prompt text lives here, never inside route functions or the service layer.
`INSIGHT_PROMPT_VERSION` is persisted on every generated Insight for
reproducibility — bump it whenever the instructions below change materially.
"""

INSIGHT_PROMPT_VERSION = "insight-v1"

_RESPONSE_SHAPE = (
    '{"insights": [{'
    '"category": "strength" | "objection" | "confusion" | "feature_request" | '
    '"uncertainty" | "disagreement", '
    '"variant_scope": "A" | "B" | "both", '
    '"title": str, "summary": str, '
    '"frequency": int, "persona_count": int, '
    '"supporting_run_ids": [int], "supporting_evidence_ids": [int], '
    '"confidence_level": "low" | "medium" | "high"'
    "}]}"
)


def build_insight_system_instructions() -> str:
    """Stable system/developer instructions for an Insight-generation call."""
    return (
        "You are a product research analyst clustering recurring qualitative signals "
        "across a set of already-completed, structured synthetic user simulation runs, "
        "for hypothesis generation and experiment planning — not market research. "
        "Rules:\n"
        "1. Cluster recurring qualitative signals (positive signals, objections, "
        "confusion, feature requests, uncertainty) into a small set of distinct "
        "insights. Distinguish recurring findings (raised by multiple runs) from "
        "isolated findings (raised by only one run) — do not inflate an isolated "
        "observation into a recurring theme.\n"
        "2. Preserve differences between Variant A and Variant B. Set variant_scope to "
        '"A" or "B" when a finding is specific to one variant, or "both" only when it '
        "genuinely recurs across both.\n"
        "3. When personas disagree with each other or with the overall variant "
        'direction, surface that as its own insight with category "disagreement".\n'
        "4. Every insight's frequency must equal the number of distinct run IDs listed "
        "in its supporting_run_ids, and persona_count must equal the number of distinct "
        "personas among those runs.\n"
        "5. Cite only the run_id values supplied in the user message under 'Allowed "
        "run_id values'. Never invent or reference any other run_id.\n"
        "6. Cite only evidence_item_id values that appear in one of your cited runs' own "
        "Evidence References. Never invent an evidence_item_id or cite one a supporting "
        "run did not itself cite.\n"
        "7. Place any interpretation not directly supported by the supplied run outputs "
        'under an insight with category "uncertainty" rather than stating it as a '
        "grounded finding.\n"
        "8. Do not invent demographic details about personas. Never claim these "
        "synthetic personas represent all users, and never claim these results validate "
        "the product in the market. Synthetic feedback supports hypothesis generation "
        "and experiment planning only — it does not replace real-user research or "
        "predict market success.\n"
        '9. Set confidence_level to "low", "medium", or "high" based on how directly '
        "the supporting runs support the insight.\n"
        "10. Return between 1 and 12 insights, with no duplicate "
        "title/category/variant_scope combination.\n"
        "11. Return ONLY a single JSON object matching this shape, with no extra "
        f"commentary or markdown formatting: {_RESPONSE_SHAPE}"
    )


def build_insight_user_prompt(context: str) -> str:
    """The user prompt for an Insight-generation call: the deterministic context, unchanged."""
    return context
