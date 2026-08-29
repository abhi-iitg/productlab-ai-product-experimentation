"""Deterministic simulation-run context builder.

Assembles exactly one run's worth of context: the project brief, the
experiment's objective/hypothesis/scenario/evaluation criteria, the single
*active* variant (never the competing one — including both would directly
steer the model toward a comparative preference), the active persona, and
only the evidence items that persona's own evidence references cite. No web
access, no hidden external context, no embeddings, no retrieval service, and
no fictional quotations — every fact comes directly from persisted rows, in
stable (evidence-ID) order.

A deterministic character limit bounds the assembled context exactly like
`app.llm.context.build_persona_context`: exceeding it raises
`SimulationContextTooLargeError` before any provider call is made, and the
caller must fail that single run safely rather than truncate silently.
"""

from app.models.evidence_item import EvidenceItem
from app.models.experiment import Experiment
from app.models.persona import Persona
from app.models.project import Project
from app.models.variant import Variant

# Deterministic total-content limit for one run's assembled context, in
# characters. Mirrors PERSONA_CONTEXT_CHAR_LIMIT's rationale — documented in
# README.md.
SIMULATION_CONTEXT_CHAR_LIMIT = 20_000


class SimulationContextTooLargeError(Exception):
    """Raised when one run's assembled context exceeds the character limit.

    Raised before any provider call is made for that run; the caller
    persists a safe failed `SimulationRun` (failure_type=context_limit) and
    continues with the remaining run matrix — content is never silently
    truncated to fit.
    """

    def __init__(self, actual_length: int, limit: int) -> None:
        self.actual_length = actual_length
        self.limit = limit
        super().__init__(
            f"Simulation context is {actual_length} characters, exceeding the "
            f"{limit}-character limit."
        )


def _format_list(values: list[str]) -> str:
    if not values:
        return "(none recorded)"
    return "\n".join(f"- {value}" for value in values)


def _format_evidence_item(item: EvidenceItem) -> str:
    source_label = item.source_label if item.source_label else "(not provided)"
    return (
        f"--- EVIDENCE ITEM START (evidence_item_id={item.id}) ---\n"
        f"Type: {item.evidence_type.value}\n"
        f"Title: {item.title}\n"
        f"Source: {source_label}\n"
        f"Content:\n{item.content}\n"
        f"--- EVIDENCE ITEM END (evidence_item_id={item.id}) ---"
    )


def build_simulation_context(
    *,
    project: Project,
    experiment: Experiment,
    variant: Variant,
    persona: Persona,
    evidence_items: list[EvidenceItem],
    char_limit: int = SIMULATION_CONTEXT_CHAR_LIMIT,
) -> str:
    """Build the deterministic context text for one simulation run.

    `evidence_items` must already be filtered to only the evidence that
    `persona`'s own evidence references cite; this function does not filter
    them itself. `evidence_items` is sorted by ID regardless of input order,
    so the same inputs always produce byte-identical context.
    """
    ordered_evidence = sorted(evidence_items, key=lambda item: item.id)
    allowed_ids = ", ".join(str(item.id) for item in ordered_evidence)
    evidence_section = "\n\n".join(_format_evidence_item(item) for item in ordered_evidence)
    if not evidence_section:
        evidence_section = "(none)"

    sections = [
        "=== PROJECT (product brief) ===",
        f"Name: {project.name}",
        f"Problem Statement: {project.problem_statement}",
        f"Target User: {project.target_user}",
        f"Product Hypothesis: {project.product_hypothesis}",
        f"Success Metric: {project.success_metric}",
        "",
        "=== PROJECT ASSUMPTIONS (author-stated, unverified — not research evidence) ===",
        _format_list(project.assumptions),
        "",
        "=== EXPERIMENT ===",
        f"Objective: {experiment.objective}",
        f"Hypothesis: {experiment.hypothesis}",
        f"Scenario: {experiment.scenario}",
        "Evaluation Criteria:",
        _format_list(experiment.evaluation_criteria),
        "",
        "=== VARIANT UNDER EVALUATION ===",
        f"Name: {variant.name}",
        f"Description: {variant.description}",
        "",
        "=== PERSONA (respond only from this bounded perspective) ===",
        f"Name: {persona.name}",
        f"Segment: {persona.segment_label}",
        f"Summary: {persona.summary}",
        "Goals:",
        _format_list(persona.goals),
        "Pain Points:",
        _format_list(persona.pain_points),
        "Constraints:",
        _format_list(persona.constraints),
        "Behaviors:",
        _format_list(persona.behaviors),
        "Unsupported Assumptions (not evidence-grounded):",
        _format_list(persona.unsupported_assumptions),
        f"Confidence Level: {persona.confidence_level.value}",
        "",
        "=== RESEARCH EVIDENCE (grounding this persona only) ===",
        f"Allowed evidence_item_id values: {allowed_ids}",
        evidence_section,
        "",
        "=== SIMULATION RULES ===",
        "- Evaluate only the variant above, in the context of the scenario above.",
        "- Respond strictly from this persona's bounded perspective — do not claim to "
        "represent all users.",
        "- Only cite evidence_item_id values listed under 'Allowed evidence_item_id "
        "values' above; never invent or reference any other ID.",
        "- Place any reasoning not directly supported by the evidence above under "
        "uncertainty_notes, not as a grounded finding.",
    ]
    context = "\n".join(sections)

    if len(context) > char_limit:
        raise SimulationContextTooLargeError(len(context), char_limit)

    return context
