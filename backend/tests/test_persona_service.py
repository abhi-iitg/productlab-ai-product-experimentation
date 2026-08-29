"""PersonaGenerationService: evidence selection, provider error translation,
atomic persistence, and rollback behavior. Never touches the network — all
generation is driven through `FakePersonaProvider`.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidRequestError,
    NotFoundError,
    ProviderConfigurationError,
    ProviderError,
)
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidOutputError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.models.evidence_item import EvidenceType
from app.schemas.evidence import EvidenceItemCreate
from app.schemas.persona import PersonaGenerateRequest
from app.schemas.project import ProjectCreate
from app.services.evidence import EvidenceService
from app.services.persona import PersonaGenerationService
from app.services.project import ProjectService
from tests.fakes import FakePersonaProvider, make_generation_result

_PROJECT_KWARGS = {
    "name": "Portfolio Discovery Tool",
    "problem_statement": "Teams decide on intuition alone.",
    "target_user": "Early-stage product managers.",
    "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
    "success_metric": "Time to a decision memo.",
}

_EVIDENCE_KWARGS = {
    "evidence_type": EvidenceType.INTERVIEW_NOTE,
    "title": "Interview with early adopter",
    "content": "They struggled with onboarding.",
}


def _create_project(db_session: Session) -> int:
    return ProjectService(db_session).create(ProjectCreate(**_PROJECT_KWARGS)).id


def _create_evidence(db_session: Session, project_id: int, **overrides: object) -> int:
    kwargs = {**_EVIDENCE_KWARGS, **overrides}
    return EvidenceService(db_session).create(project_id, EvidenceItemCreate(**kwargs)).id


def test_generate_persists_all_personas(db_session: Session) -> None:
    project_id = _create_project(db_session)
    evidence_id = _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id))
    service = PersonaGenerationService(db_session, provider)

    personas = service.generate(project_id, PersonaGenerateRequest(persona_count=2))

    assert len(personas) == 2
    for persona in personas:
        assert persona.id is not None
        assert persona.project_id == project_id
        assert persona.prompt_version == "persona-v1"
        assert persona.model_name == provider.model_name

    persisted = service.list_for_project(project_id)
    assert len(persisted) == 2


def test_generate_uses_all_project_evidence_when_ids_omitted(db_session: Session) -> None:
    project_id = _create_project(db_session)
    evidence_id_1 = _create_evidence(db_session, project_id, title="First")
    evidence_id_2 = _create_evidence(db_session, project_id, title="Second")
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id_1))
    service = PersonaGenerationService(db_session, provider)

    service.generate(project_id, PersonaGenerateRequest(persona_count=2))

    call = provider.calls[0]
    assert call["allowed_evidence_ids"] == {evidence_id_1, evidence_id_2}


def test_generate_respects_selected_evidence_ids(db_session: Session) -> None:
    project_id = _create_project(db_session)
    evidence_id_1 = _create_evidence(db_session, project_id, title="First")
    _create_evidence(db_session, project_id, title="Second")
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id_1))
    service = PersonaGenerationService(db_session, provider)

    service.generate(
        project_id,
        PersonaGenerateRequest(persona_count=2, selected_evidence_ids=[evidence_id_1]),
    )

    call = provider.calls[0]
    assert call["allowed_evidence_ids"] == {evidence_id_1}


def test_generate_raises_not_found_for_missing_project(db_session: Session) -> None:
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=1))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(NotFoundError):
        service.generate(999, PersonaGenerateRequest(persona_count=2))


def test_generate_raises_invalid_request_when_project_has_no_evidence(db_session: Session) -> None:
    project_id = _create_project(db_session)
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=1))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(InvalidRequestError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert provider.calls == []


def test_generate_raises_invalid_request_for_evidence_not_owned_by_project(
    db_session: Session,
) -> None:
    project_a = _create_project(db_session)
    project_b = _create_project(db_session)
    evidence_from_b = _create_evidence(db_session, project_b)
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=1))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(InvalidRequestError):
        service.generate(
            project_a,
            PersonaGenerateRequest(persona_count=2, selected_evidence_ids=[evidence_from_b]),
        )
    assert provider.calls == []


def test_generate_raises_provider_error_for_unsupported_evidence_reference(
    db_session: Session,
) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    # The fake simulates the OpenAI provider's own local schema validation
    # rejecting output that cites an evidence ID outside the supplied context.
    provider = FakePersonaProvider(
        error=LLMInvalidOutputError("cited an evidence_item_id outside the allowed set")
    )
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_raises_provider_error_for_malformed_json(db_session: Session) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(error=LLMInvalidOutputError("malformed JSON"))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_raises_provider_error_for_invalid_schema(db_session: Session) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(error=LLMInvalidOutputError("schema-invalid output"))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_raises_provider_error_for_empty_output(db_session: Session) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(error=LLMEmptyOutputError("empty output"))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_raises_provider_error_for_timeout(db_session: Session) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(error=LLMTimeoutError("timed out"))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_raises_provider_error_for_rate_limit(db_session: Session) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(error=LLMRateLimitError("rate limited"))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_raises_provider_error_for_status_failure(db_session: Session) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(error=LLMStatusError("bad status"))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_raises_provider_configuration_error_for_missing_config(
    db_session: Session,
) -> None:
    project_id = _create_project(db_session)
    _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(error=LLMConfigurationError("no API key"))
    service = PersonaGenerationService(db_session, provider)

    with pytest.raises(ProviderConfigurationError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))
    assert service.list_for_project(project_id) == []


def test_generate_rolls_back_and_persists_nothing_on_commit_failure(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = _create_project(db_session)
    evidence_id = _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id))
    service = PersonaGenerationService(db_session, provider)

    rollback_calls: list[bool] = []
    original_rollback = db_session.rollback

    def spy_rollback() -> None:
        rollback_calls.append(True)
        original_rollback()

    def failing_commit() -> None:
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    monkeypatch.setattr(db_session, "rollback", spy_rollback)

    with pytest.raises(RuntimeError):
        service.generate(project_id, PersonaGenerateRequest(persona_count=2))

    assert rollback_calls == [True]


def test_get_raises_not_found_across_projects(db_session: Session) -> None:
    project_a = _create_project(db_session)
    project_b = _create_project(db_session)
    evidence_id = _create_evidence(db_session, project_a)
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id))
    service = PersonaGenerationService(db_session, provider)
    persona = service.generate(project_a, PersonaGenerateRequest(persona_count=2))[0]

    with pytest.raises(NotFoundError):
        service.get(project_b, persona.id)


def test_delete_removes_persona(db_session: Session) -> None:
    project_id = _create_project(db_session)
    evidence_id = _create_evidence(db_session, project_id)
    provider = FakePersonaProvider(result=make_generation_result(evidence_item_id=evidence_id))
    service = PersonaGenerationService(db_session, provider)
    persona = service.generate(project_id, PersonaGenerateRequest(persona_count=2))[0]

    service.delete(project_id, persona.id)

    with pytest.raises(NotFoundError):
        service.get(project_id, persona.id)
