"""Deterministic simulation-run context builder."""

import pytest

from app.llm.simulation_context import SimulationContextTooLargeError, build_simulation_context
from app.models.evidence_item import EvidenceItem, EvidenceType
from app.models.experiment import Experiment
from app.models.persona import ConfidenceLevel, Persona
from app.models.project import Project
from app.models.variant import Variant, VariantKey


def _project(**overrides: object) -> Project:
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


def _experiment(**overrides: object) -> Experiment:
    defaults: dict[str, object] = {
        "id": 1,
        "project_id": 1,
        "name": "Onboarding concept comparison",
        "objective": "Compare two onboarding approaches",
        "hypothesis": "A guided setup will improve clarity",
        "scenario": "Evaluate the onboarding flow.",
        "evaluation_criteria": ["Clarity", "Adoption intent"],
        "repeat_count": 1,
    }
    defaults.update(overrides)
    return Experiment(**defaults)


def _variant(key: VariantKey = VariantKey.A, **overrides: object) -> Variant:
    defaults: dict[str, object] = {
        "id": 1,
        "experiment_id": 1,
        "key": key,
        "name": "Self-service onboarding" if key == VariantKey.A else "Guided onboarding",
        "description": "No guidance." if key == VariantKey.A else "Step-by-step wizard.",
    }
    defaults.update(overrides)
    return Variant(**defaults)


def _persona(evidence_item_id: int = 1, **overrides: object) -> Persona:
    defaults: dict[str, object] = {
        "id": 1,
        "project_id": 1,
        "name": "Alex the Adopter",
        "segment_label": "Early Adopter",
        "summary": "An early adopter evaluating the product.",
        "goals": ["Understand the value quickly."],
        "pain_points": ["Confusing onboarding."],
        "constraints": ["Limited evaluation time."],
        "behaviors": ["Reads reviews before adopting tools."],
        "evidence_references": [
            {"evidence_item_id": evidence_item_id, "supported_claims": ["Struggled."]}
        ],
        "unsupported_assumptions": ["Likely price-sensitive."],
        "confidence_level": ConfidenceLevel.MEDIUM,
        "prompt_version": "persona-v1",
        "model_name": "fake-model-v1",
    }
    defaults.update(overrides)
    return Persona(**defaults)


def _evidence(evidence_id: int, **overrides: object) -> EvidenceItem:
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


def test_build_simulation_context_is_stable_for_same_input() -> None:
    args = dict(
        project=_project(),
        experiment=_experiment(),
        variant=_variant(),
        persona=_persona(),
        evidence_items=[_evidence(1)],
    )
    assert build_simulation_context(**args) == build_simulation_context(**args)


def test_build_simulation_context_includes_project_and_experiment_fields() -> None:
    project = _project()
    experiment = _experiment()
    context = build_simulation_context(
        project=project,
        experiment=experiment,
        variant=_variant(),
        persona=_persona(),
        evidence_items=[_evidence(1)],
    )

    assert project.name in context
    assert project.problem_statement in context
    assert experiment.objective in context
    assert experiment.hypothesis in context
    assert experiment.scenario in context
    assert "Clarity" in context


def test_build_simulation_context_includes_only_active_variant() -> None:
    variant_a = _variant(VariantKey.A)
    context = build_simulation_context(
        project=_project(),
        experiment=_experiment(),
        variant=variant_a,
        persona=_persona(),
        evidence_items=[_evidence(1)],
    )

    assert variant_a.name in context
    assert variant_a.description in context
    # The competing Variant B's copy must never appear in a single run's context.
    assert "Guided onboarding" not in context
    assert "Step-by-step wizard." not in context


def test_build_simulation_context_includes_persona_fields() -> None:
    persona = _persona()
    context = build_simulation_context(
        project=_project(),
        experiment=_experiment(),
        variant=_variant(),
        persona=persona,
        evidence_items=[_evidence(1)],
    )

    assert persona.name in context
    assert persona.summary in context
    assert "Understand the value quickly." in context
    assert "Confusing onboarding." in context
    assert "Limited evaluation time." in context
    assert "Reads reviews before adopting tools." in context
    assert "Likely price-sensitive." in context
    assert "medium" in context


def test_build_simulation_context_includes_only_persona_referenced_evidence() -> None:
    persona = _persona(evidence_item_id=1)
    context = build_simulation_context(
        project=_project(),
        experiment=_experiment(),
        variant=_variant(),
        persona=persona,
        evidence_items=[_evidence(1)],
    )

    assert "evidence_item_id=1" in context
    # Evidence 2 was never passed in (not referenced by this persona).
    assert "evidence_item_id=2" not in context


def test_build_simulation_context_separates_assumptions_from_evidence() -> None:
    project = _project(assumptions=["Users prefer mobile."])
    context = build_simulation_context(
        project=project,
        experiment=_experiment(),
        variant=_variant(),
        persona=_persona(),
        evidence_items=[_evidence(1, content="Users mentioned preferring desktop.")],
    )

    assumptions_index = context.index("PROJECT ASSUMPTIONS")
    evidence_index = context.index("RESEARCH EVIDENCE")
    assert assumptions_index < evidence_index
    assert "Users prefer mobile." in context


def test_build_simulation_context_raises_when_over_limit() -> None:
    persona = _persona()
    with pytest.raises(SimulationContextTooLargeError):
        build_simulation_context(
            project=_project(),
            experiment=_experiment(),
            variant=_variant(),
            persona=persona,
            evidence_items=[_evidence(1, content="x" * 1000)],
            char_limit=100,
        )


def test_build_simulation_context_does_not_truncate_when_over_limit() -> None:
    with pytest.raises(SimulationContextTooLargeError) as exc_info:
        build_simulation_context(
            project=_project(),
            experiment=_experiment(),
            variant=_variant(),
            persona=_persona(),
            evidence_items=[_evidence(1, content="x" * 1000)],
            char_limit=100,
        )

    assert exc_info.value.actual_length > 100
    assert exc_info.value.limit == 100


def test_build_simulation_context_stays_within_default_limit_for_small_input() -> None:
    context = build_simulation_context(
        project=_project(),
        experiment=_experiment(),
        variant=_variant(),
        persona=_persona(),
        evidence_items=[_evidence(1)],
    )
    assert len(context) < 20_000
