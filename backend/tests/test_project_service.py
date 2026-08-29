"""ProjectService: not-found behavior and transaction ownership."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project import ProjectService

_CREATE_KWARGS = {
    "name": "Portfolio Discovery Tool",
    "problem_statement": "Teams decide on intuition alone.",
    "target_user": "Early-stage product managers.",
    "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
    "success_metric": "Time to a decision memo.",
}


def test_create_commits_and_returns_persisted_project(db_session: Session) -> None:
    service = ProjectService(db_session)

    project = service.create(ProjectCreate(**_CREATE_KWARGS))

    assert project.id is not None
    assert service.get(project.id).id == project.id


def test_get_raises_not_found_for_missing_project(db_session: Session) -> None:
    service = ProjectService(db_session)

    with pytest.raises(NotFoundError):
        service.get(999)


def test_update_raises_not_found_for_missing_project(db_session: Session) -> None:
    service = ProjectService(db_session)

    with pytest.raises(NotFoundError):
        service.update(999, ProjectUpdate(name="New Name"))


def test_delete_raises_not_found_for_missing_project(db_session: Session) -> None:
    service = ProjectService(db_session)

    with pytest.raises(NotFoundError):
        service.delete(999)


def test_update_applies_only_provided_fields(db_session: Session) -> None:
    service = ProjectService(db_session)
    project = service.create(ProjectCreate(**_CREATE_KWARGS))

    updated = service.update(project.id, ProjectUpdate(name="Renamed Tool"))

    assert updated.name == "Renamed Tool"
    assert updated.problem_statement == _CREATE_KWARGS["problem_statement"]


def test_delete_removes_project(db_session: Session) -> None:
    service = ProjectService(db_session)
    project = service.create(ProjectCreate(**_CREATE_KWARGS))

    service.delete(project.id)

    with pytest.raises(NotFoundError):
        service.get(project.id)


def test_update_rolls_back_session_on_commit_failure(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ProjectService(db_session)
    project = service.create(ProjectCreate(**_CREATE_KWARGS))

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
        service.update(project.id, ProjectUpdate(name="Should Not Persist"))

    assert rollback_calls == [True]
