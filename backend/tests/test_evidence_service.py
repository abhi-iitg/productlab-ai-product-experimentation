"""EvidenceService: project scoping, not-found behavior, cross-project isolation."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.evidence_item import EvidenceType
from app.schemas.evidence import EvidenceItemCreate, EvidenceItemUpdate
from app.schemas.project import ProjectCreate
from app.services.evidence import EvidenceService
from app.services.project import ProjectService

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


def test_create_raises_not_found_for_missing_project(db_session: Session) -> None:
    service = EvidenceService(db_session)

    with pytest.raises(NotFoundError):
        service.create(999, EvidenceItemCreate(**_EVIDENCE_KWARGS))


def test_create_and_get_round_trip(db_session: Session) -> None:
    project_id = _create_project(db_session)
    service = EvidenceService(db_session)

    created = service.create(project_id, EvidenceItemCreate(**_EVIDENCE_KWARGS))
    fetched = service.get(project_id, created.id)

    assert fetched.id == created.id
    assert fetched.project_id == project_id


def test_list_for_project_raises_not_found_for_missing_project(db_session: Session) -> None:
    service = EvidenceService(db_session)

    with pytest.raises(NotFoundError):
        service.list_for_project(999)


def test_get_raises_not_found_for_missing_evidence(db_session: Session) -> None:
    project_id = _create_project(db_session)
    service = EvidenceService(db_session)

    with pytest.raises(NotFoundError):
        service.get(project_id, 999)


def test_evidence_not_retrievable_through_another_projects_id(db_session: Session) -> None:
    project_a = _create_project(db_session)
    project_b = _create_project(db_session)
    service = EvidenceService(db_session)
    evidence = service.create(project_a, EvidenceItemCreate(**_EVIDENCE_KWARGS))

    with pytest.raises(NotFoundError):
        service.get(project_b, evidence.id)


def test_evidence_not_updatable_through_another_projects_id(db_session: Session) -> None:
    project_a = _create_project(db_session)
    project_b = _create_project(db_session)
    service = EvidenceService(db_session)
    evidence = service.create(project_a, EvidenceItemCreate(**_EVIDENCE_KWARGS))

    with pytest.raises(NotFoundError):
        service.update(project_b, evidence.id, EvidenceItemUpdate(title="Hijacked"))


def test_update_applies_only_provided_fields(db_session: Session) -> None:
    project_id = _create_project(db_session)
    service = EvidenceService(db_session)
    evidence = service.create(project_id, EvidenceItemCreate(**_EVIDENCE_KWARGS))

    updated = service.update(project_id, evidence.id, EvidenceItemUpdate(title="New Title"))

    assert updated.title == "New Title"
    assert updated.content == _EVIDENCE_KWARGS["content"]


def test_delete_removes_evidence(db_session: Session) -> None:
    project_id = _create_project(db_session)
    service = EvidenceService(db_session)
    evidence = service.create(project_id, EvidenceItemCreate(**_EVIDENCE_KWARGS))

    service.delete(project_id, evidence.id)

    with pytest.raises(NotFoundError):
        service.get(project_id, evidence.id)


def test_update_rolls_back_session_on_commit_failure(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = _create_project(db_session)
    service = EvidenceService(db_session)
    evidence = service.create(project_id, EvidenceItemCreate(**_EVIDENCE_KWARGS))

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
        service.update(project_id, evidence.id, EvidenceItemUpdate(title="Should Not Persist"))

    assert rollback_calls == [True]
