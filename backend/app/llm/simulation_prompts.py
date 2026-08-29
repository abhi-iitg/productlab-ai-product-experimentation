"""Simulation-run prompt template and version tracking.

Prompt text lives here, never inside route functions or the service layer.
`SIMULATION_PROMPT_VERSION` is persisted on every simulation run (completed
or failed) for reproducibility — bump it whenever the instructions below
change materially.

Two things are kept deliberately separate, mirroring `app.llm.prompts`:
- `build_simulation_system_instructions` — stable system/developer
  instructions.
- The project/experiment/variant/persona/evidence context — built by
  `app.llm.simulation_context`, not this module, and passed through
  `build_simulation_user_prompt` unchanged. There is no free-text user
  input analogous to persona generation's `focus`: the user prompt is
  built entirely from already-persisted, already-validated experiment
  fields.
"""

SIMULATION_PROMPT_VERSION = "simulation-v1"

_RESPONSE_SHAPE = (
    "{"
    '"task_outcome": "completed" | "partially_completed" | "failed" | "uncertain", '
    '"clarity_score": int (1-5), '
    '"perceived_value_score": int (1-5), '
    '"adoption_intent_score": int (1-5), '
    '"response_summary": str, '
    '"positive_signals": [str], "objections": [str], "confusion_points": [str], '
    '"feature_requests": [str], "uncertainty_notes": [str], '
    '"evidence_references": [{"evidence_item_id": int, "supported_claims": [str]}]'
    "}"
)


def build_simulation_system_instructions() -> str:
    """Stable system/developer instructions for a simulation-run call."""
    return (
        "You are simulating one synthetic user's structured reaction to a single product "
        "concept variant, for early hypothesis generation and experiment planning — not "
        "market research. Rules:\n"
        "1. Evaluate only the supplied variant against the supplied scenario. Do not "
        "compare it to any alternative — none is provided to you.\n"
        "2. Respond strictly from the bounded perspective of the supplied persona: its "
        "goals, pain points, constraints, and behaviors. Do not invent demographic or "
        "biographical details beyond what the persona states.\n"
        "3. Rely on the supplied research evidence where possible. Any reasoning that is "
        "not directly supported by the persona or the supplied evidence belongs under "
        "uncertainty_notes — never state it as a grounded finding.\n"
        "4. Cite evidence only by the evidence_item_id values supplied in the user "
        "message. Never invent an evidence_item_id or cite one that was not supplied.\n"
        "5. Never claim to represent all users of the product, and never claim that this "
        "simulated reaction validates the product in the market. Synthetic feedback "
        "supports hypothesis generation and experiment planning only — it does not "
        "replace real-user research or predict market success.\n"
        "6. Score clarity_score, perceived_value_score, and adoption_intent_score from 1 "
        "(lowest) to 5 (highest), based only on this persona's reaction to this variant.\n"
        "7. Return ONLY a single JSON object matching this shape, with no extra "
        f"commentary or markdown formatting: {_RESPONSE_SHAPE}"
    )


def build_simulation_user_prompt(context: str) -> str:
    """The user prompt for a simulation-run call: the deterministic context, unchanged."""
    return context
