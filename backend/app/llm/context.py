"""Deterministic persona-generation context builder.

Assembles the project brief and selected evidence into a single plain-text
block sent to the LLM as part of the user prompt. No vector database, no
embeddings, no retrieval service, no external or web information — every
fact in the context comes directly from the project's own persisted
`Project` and `EvidenceItem` rows, in stable (evidence-ID) order.

A deterministic character limit bounds the assembled context so a project
with a very large evidence library can't silently blow up token cost/
latency, or get silently truncated (which would let evidence content
disappear from the prompt without anyone knowing). Exceeding the limit
raises `PersonaContextTooLargeError` before any provider call is made.
"""

from app.models.evidence_item import EvidenceItem
from app.models.project import Project

# Deterministic total-content limit for the assembled context, in
# characters. Chosen to comfortably fit a realistic small evidence library
# while staying well under typical model context windows, without depending
# on a tokenizer. Documented in README.md.
PERSONA_CONTEXT_CHAR_LIMIT = 20_000


class PersonaContextTooLargeError(Exception):
    """Raised when the assembled context exceeds `PERSONA_CONTEXT_CHAR_LIMIT`.

    Raised before any provider call is made; evidence content is never
    silently truncated to fit.
    """

    def __init__(self, actual_length: int, limit: int) -> None:
        self.actual_length = actual_length
        self.limit = limit
        super().__init__(
            f"Persona generation context is {actual_length} characters, exceeding the "
            f"{limit}-character limit. Select fewer or shorter evidence items."
        )


def _format_assumptions(assumptions: list[str]) -> str:
    if not assumptions:
        return "(No assumptions recorded.)"
    return "\n".join(f"- {assumption}" for assumption in assumptions)


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


def build_persona_context(
    project: Project,
    evidence_items: list[EvidenceItem],
    *,
    char_limit: int = PERSONA_CONTEXT_CHAR_LIMIT,
) -> str:
    """Build the deterministic project+evidence context text.

    `evidence_items` is sorted by ID regardless of input order, so the same
    project and evidence selection always produces byte-identical context.
    """
    ordered_evidence = sorted(evidence_items, key=lambda item: item.id)
    allowed_ids = ", ".join(str(item.id) for item in ordered_evidence)
    evidence_section = "\n\n".join(_format_evidence_item(item) for item in ordered_evidence)

    sections = [
        "=== PROJECT (product brief) ===",
        f"Name: {project.name}",
        f"Problem Statement: {project.problem_statement}",
        f"Target User: {project.target_user}",
        f"Product Hypothesis: {project.product_hypothesis}",
        f"Success Metric: {project.success_metric}",
        "",
        "=== PRODUCT ASSUMPTIONS (author-stated, unverified — not research evidence) ===",
        _format_assumptions(project.assumptions),
        "",
        "=== RESEARCH EVIDENCE (the sole grounding source for personas) ===",
        f"Allowed evidence_item_id values: {allowed_ids}",
        evidence_section,
        "",
        "=== GENERATION RULES ===",
        "- Personas must be grounded in the research evidence above, not the product assumptions.",
        "- Only cite evidence_item_id values listed under 'Allowed evidence_item_id values' "
        "above; never invent or reference any other ID.",
        "- Any detail you include that is not directly traceable to the evidence above must "
        "be listed under unsupported_assumptions, not stated as a grounded finding.",
    ]
    context = "\n".join(sections)

    if len(context) > char_limit:
        raise PersonaContextTooLargeError(len(context), char_limit)

    return context
