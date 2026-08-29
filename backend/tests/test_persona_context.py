"""Deterministic persona-generation context builder."""

import pytest

from app.llm.context import PersonaContextTooLargeError, build_persona_context
from app.models.evidence_item import EvidenceItem, EvidenceType
from app.models.project import Project


def _make_project(**overrides: object) -> Project:
    defaults: dict[str, object] = {
        "id": 1,
        "name": "Portfolio Discovery Tool",
        "problem_statement": "Teams decide on intuition alone.",
        "target_user": "Early-stage product managers.",
        "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
        "success_metric": "Time to a decision memo.",
        "assumptions": ["Users have existing evidence."],
    }
    defaults.update(overrides)
    return Project(**defaults)


def _make_evidence(evidence_id: int, **overrides: object) -> EvidenceItem:
    defaults: dict[str, object] = {
        "id": evidence_id,
        "project_id": 1,
        "evidence_type": EvidenceType.INTERVIEW_NOTE,
        "title": f"Evidence {evidence_id}",
        "content": f"Content for evidence {evidence_id}.",
        "source_label": None,
    }
    defaults.update(overrides)
    return EvidenceItem(**defaults)


def test_build_persona_context_is_stable_for_same_input() -> None:
    project = _make_project()
    evidence = [_make_evidence(1), _make_evidence(2)]

    first = build_persona_context(project, evidence)
    second = build_persona_context(project, evidence)

    assert first == second


def test_build_persona_context_includes_project_fields() -> None:
    project = _make_project()
    context = build_persona_context(project, [_make_evidence(1)])

    assert project.name in context
    assert project.problem_statement in context
    assert project.target_user in context
    assert project.product_hypothesis in context
    assert project.success_metric in context


def test_build_persona_context_includes_evidence_ids_and_content() -> None:
    project = _make_project()
    evidence = _make_evidence(7, title="Interview notes", content="Users struggled to sign up.")
    context = build_persona_context(project, [evidence])

    assert "evidence_item_id=7" in context
    assert "Interview notes" in context
    assert "Users struggled to sign up." in context


def test_build_persona_context_orders_evidence_by_id_regardless_of_input_order() -> None:
    project = _make_project()
    evidence = [_make_evidence(3), _make_evidence(1), _make_evidence(2)]

    context = build_persona_context(project, evidence)

    first_index = context.index("evidence_item_id=1")
    second_index = context.index("evidence_item_id=2")
    third_index = context.index("evidence_item_id=3")
    assert first_index < second_index < third_index


def test_build_persona_context_shows_source_label_when_present() -> None:
    project = _make_project()
    evidence = _make_evidence(1, source_label="Zoom call, 2026-06-01")

    context = build_persona_context(project, [evidence])

    assert "Zoom call, 2026-06-01" in context


def test_build_persona_context_shows_placeholder_when_source_label_missing() -> None:
    project = _make_project()
    evidence = _make_evidence(1, source_label=None)

    context = build_persona_context(project, [evidence])

    assert "Source: (not provided)" in context


def test_build_persona_context_separates_assumptions_from_evidence() -> None:
    project = _make_project(assumptions=["Users prefer mobile."])
    evidence = _make_evidence(1, content="Users mentioned preferring desktop.")

    context = build_persona_context(project, [evidence])

    assumptions_index = context.index("PRODUCT ASSUMPTIONS")
    evidence_index = context.index("RESEARCH EVIDENCE")
    assert assumptions_index < evidence_index
    assert "Users prefer mobile." in context


def test_build_persona_context_handles_no_assumptions() -> None:
    project = _make_project(assumptions=[])
    context = build_persona_context(project, [_make_evidence(1)])

    assert "(No assumptions recorded.)" in context


def test_build_persona_context_raises_when_over_limit() -> None:
    project = _make_project()
    evidence = _make_evidence(1, content="x" * 1000)

    with pytest.raises(PersonaContextTooLargeError):
        build_persona_context(project, [evidence], char_limit=100)


def test_build_persona_context_does_not_truncate_when_over_limit() -> None:
    """The error carries the actual length; content is never silently cut."""
    project = _make_project()
    evidence = _make_evidence(1, content="x" * 1000)

    with pytest.raises(PersonaContextTooLargeError) as exc_info:
        build_persona_context(project, [evidence], char_limit=100)

    assert exc_info.value.actual_length > 100
    assert exc_info.value.limit == 100


def test_build_persona_context_stays_within_default_limit_for_small_evidence() -> None:
    project = _make_project()
    context = build_persona_context(project, [_make_evidence(1), _make_evidence(2)])

    assert len(context) < 20_000
