"""Persona-generation prompt template and version tracking.

Prompt text lives here, never inside route functions or the service layer,
so it stays a single reviewable, testable unit. `PERSONA_PROMPT_VERSION` is
persisted on every generated persona for reproducibility — bump it whenever
the instructions below change materially.

Three things are kept deliberately separate:
- `build_system_instructions` — stable system/developer instructions.
- The project+evidence context — built by `app.llm.context`, not this
  module.
- `build_user_prompt` — combines that context with optional user-controlled
  `focus` text, in its own clearly labeled section so free-text user input
  is never confused with research evidence.
"""

PERSONA_PROMPT_VERSION = "persona-v1"

_RESPONSE_SHAPE = (
    '{"personas": [{'
    '"name": str, "segment_label": str, "summary": str, '
    '"goals": [str], "pain_points": [str], "constraints": [str], "behaviors": [str], '
    '"evidence_references": [{"evidence_item_id": int, "supported_claims": [str]}], '
    '"unsupported_assumptions": [str], '
    '"confidence_level": "low" | "medium" | "high"'
    "}]}"
)


def build_system_instructions(persona_count: int) -> str:
    """Stable system/developer instructions for a persona-generation call."""
    return (
        "You are a product research assistant that generates evidence-grounded synthetic "
        "user personas for a product discovery platform.\n\n"
        f"Generate exactly {persona_count} distinct personas from the research evidence "
        "supplied in the user message. Rules:\n"
        "1. Every persona must be grounded in the supplied research evidence, not invented. "
        "Do not invent demographic details (age, location, job title, etc.) unless the "
        "evidence directly supports them.\n"
        "2. Make personas distinct from one another — do not restate the same person with "
        "different names.\n"
        "3. Every claim under goals, pain_points, constraints, and behaviors must be "
        "traceable to the supplied evidence. Anything you include that is not directly "
        "supported by the evidence belongs under unsupported_assumptions instead — never "
        "present it as a grounded finding.\n"
        "4. Cite evidence only by the evidence_item_id values supplied in the user message. "
        "Never invent an evidence_item_id or cite one that was not supplied.\n"
        '5. Set confidence_level to "low", "medium", or "high" based on how directly the '
        "evidence supports the persona.\n"
        "6. Do not claim or imply that these personas represent all users of the product, "
        "and never claim they validate the product in the market. Synthetic feedback "
        "supports hypothesis generation and experiment planning only — it does not replace "
        "real-user research or predict market success.\n"
        "7. Return ONLY a single JSON object matching this shape, with no extra commentary "
        f"or markdown formatting: {_RESPONSE_SHAPE}"
    )


def build_user_prompt(context: str, focus: str | None) -> str:
    """Combine the deterministic project/evidence context with optional user focus."""
    focus_section = focus if focus else "(none provided)"
    return f"{context}\n\n=== OPTIONAL FOCUS (user-provided, not evidence) ===\n{focus_section}"
