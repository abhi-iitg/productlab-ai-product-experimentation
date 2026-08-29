"""Pydantic schema validation for Persona generation."""

import pytest
from pydantic import ValidationError

from app.models.persona import ConfidenceLevel
from app.schemas.persona import (
    EvidenceReference,
    GeneratedPersona,
    PersonaGenerateRequest,
    PersonaGenerationResult,
)


def _persona_kwargs(**overrides: object) -> dict:
    defaults: dict[str, object] = {
        "name": "Alex the Adopter",
        "segment_label": "Early Adopter",
        "summary": "An early adopter evaluating the product.",
        "goals": ["Understand the value quickly."],
        "pain_points": ["Confusing onboarding."],
        "constraints": ["Limited evaluation time."],
        "behaviors": ["Reads reviews before adopting tools."],
        "evidence_references": [
            EvidenceReference(evidence_item_id=1, supported_claims=["Struggled with onboarding."])
        ],
        "unsupported_assumptions": ["Likely price-sensitive."],
        "confidence_level": ConfidenceLevel.MEDIUM,
    }
    defaults.update(overrides)
    return defaults


# --- EvidenceReference -------------------------------------------------


def test_evidence_reference_normalizes_and_dedupes_claims() -> None:
    ref = EvidenceReference(
        evidence_item_id=1,
        supported_claims=["  Claim one.  ", "claim one.", "Claim two."],
    )
    assert ref.supported_claims == ["Claim one.", "Claim two."]


def test_evidence_reference_rejects_all_blank_claims() -> None:
    with pytest.raises(ValidationError):
        EvidenceReference(evidence_item_id=1, supported_claims=["   ", ""])


def test_evidence_reference_accepts_id_in_allowed_context() -> None:
    ref = EvidenceReference.model_validate(
        {"evidence_item_id": 5, "supported_claims": ["Claim."]},
        context={"allowed_evidence_ids": {5, 6}},
    )
    assert ref.evidence_item_id == 5


def test_evidence_reference_rejects_id_outside_allowed_context() -> None:
    with pytest.raises(ValidationError):
        EvidenceReference.model_validate(
            {"evidence_item_id": 99, "supported_claims": ["Claim."]},
            context={"allowed_evidence_ids": {5, 6}},
        )


def test_evidence_reference_skips_allowed_check_without_context() -> None:
    # Reading a persisted persona back has no context — must not fail.
    ref = EvidenceReference.model_validate({"evidence_item_id": 999, "supported_claims": ["C."]})
    assert ref.evidence_item_id == 999


# --- GeneratedPersona ----------------------------------------------------


def test_generated_persona_accepts_valid_data() -> None:
    persona = GeneratedPersona(**_persona_kwargs())
    assert persona.name == "Alex the Adopter"
    assert persona.confidence_level == ConfidenceLevel.MEDIUM


@pytest.mark.parametrize("field", ["name", "segment_label", "summary"])
def test_generated_persona_rejects_blank_required_strings(field: str) -> None:
    with pytest.raises(ValidationError):
        GeneratedPersona(**_persona_kwargs(**{field: "   "}))


def test_generated_persona_normalizes_and_dedupes_goals() -> None:
    persona = GeneratedPersona(
        **_persona_kwargs(goals=["  Goal one  ", "goal one", "", "Goal two"])
    )
    assert persona.goals == ["Goal one", "Goal two"]


def test_generated_persona_normalizes_unsupported_assumptions() -> None:
    persona = GeneratedPersona(
        **_persona_kwargs(unsupported_assumptions=["  Assumption  ", "assumption", ""])
    )
    assert persona.unsupported_assumptions == ["Assumption"]


def test_generated_persona_rejects_invalid_confidence_level() -> None:
    with pytest.raises(ValidationError):
        GeneratedPersona(**_persona_kwargs(confidence_level="extreme"))


@pytest.mark.parametrize("level", ["low", "medium", "high"])
def test_generated_persona_accepts_every_confidence_level(level: str) -> None:
    persona = GeneratedPersona(**_persona_kwargs(confidence_level=level))
    assert persona.confidence_level == ConfidenceLevel(level)


def test_generated_persona_requires_at_least_one_evidence_reference() -> None:
    with pytest.raises(ValidationError):
        GeneratedPersona(**_persona_kwargs(evidence_references=[]))


# --- PersonaGenerationResult ----------------------------------------------


def test_persona_generation_result_rejects_empty_personas_list() -> None:
    with pytest.raises(ValidationError):
        PersonaGenerationResult(personas=[])


def test_persona_generation_result_rejects_entire_result_on_one_invalid_reference() -> None:
    valid = GeneratedPersona(**_persona_kwargs())
    invalid_data = _persona_kwargs(
        evidence_references=[
            {"evidence_item_id": 999, "supported_claims": ["Unsupported reference."]}
        ]
    )
    with pytest.raises(ValidationError):
        PersonaGenerationResult.model_validate(
            {"personas": [valid.model_dump(), invalid_data]},
            context={"allowed_evidence_ids": {1}},
        )


def test_persona_generation_result_accepts_all_valid_references_in_context() -> None:
    result = PersonaGenerationResult.model_validate(
        {"personas": [_persona_kwargs()]},
        context={"allowed_evidence_ids": {1}},
    )
    assert len(result.personas) == 1


# --- PersonaGenerateRequest ------------------------------------------------


def test_generate_request_accepts_valid_payload() -> None:
    request = PersonaGenerateRequest(persona_count=3, selected_evidence_ids=[1, 2], focus="  B2B  ")
    assert request.persona_count == 3
    assert request.selected_evidence_ids == [1, 2]
    assert request.focus == "B2B"


@pytest.mark.parametrize("count", [1, 6, 0, -1])
def test_generate_request_rejects_persona_count_outside_range(count: int) -> None:
    with pytest.raises(ValidationError):
        PersonaGenerateRequest(persona_count=count)


@pytest.mark.parametrize("count", [2, 3, 4, 5])
def test_generate_request_accepts_every_valid_persona_count(count: int) -> None:
    request = PersonaGenerateRequest(persona_count=count)
    assert request.persona_count == count


def test_generate_request_rejects_empty_selected_evidence_list() -> None:
    with pytest.raises(ValidationError):
        PersonaGenerateRequest(persona_count=2, selected_evidence_ids=[])


def test_generate_request_rejects_duplicate_selected_evidence_ids() -> None:
    with pytest.raises(ValidationError):
        PersonaGenerateRequest(persona_count=2, selected_evidence_ids=[1, 1, 2])


def test_generate_request_allows_omitted_selected_evidence_ids() -> None:
    request = PersonaGenerateRequest(persona_count=2)
    assert request.selected_evidence_ids is None


def test_generate_request_normalizes_blank_focus_to_none() -> None:
    request = PersonaGenerateRequest(persona_count=2, focus="   ")
    assert request.focus is None


def test_generate_request_allows_explicit_none_for_optional_fields() -> None:
    request = PersonaGenerateRequest(persona_count=2, selected_evidence_ids=None, focus=None)
    assert request.selected_evidence_ids is None
    assert request.focus is None
