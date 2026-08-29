"""ProjectRepository persistence behavior."""

from sqlalchemy.orm import Session

from app.models.project import ProjectStatus
from app.repositories.project import ProjectRepository

_CREATE_DATA = {
    "name": "Portfolio Discovery Tool",
    "problem_statement": "Teams decide on intuition alone.",
    "target_user": "Early-stage product managers.",
    "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
    "success_metric": "Time to a decision memo.",
    "assumptions": ["Users have existing evidence."],
    "status": ProjectStatus.DRAFT,
}


def test_create_flushes_and_assigns_id(db_session: Session) -> None:
    repo = ProjectRepository(db_session)

    project = repo.create(dict(_CREATE_DATA))

    assert project.id is not None


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = ProjectRepository(db_session)
    assert repo.get_by_id(999) is None


def test_get_by_id_returns_created_project(db_session: Session) -> None:
    repo = ProjectRepository(db_session)
    project = repo.create(dict(_CREATE_DATA))
    db_session.commit()

    fetched = repo.get_by_id(project.id)

    assert fetched is not None
    assert fetched.id == project.id


def test_list_returns_projects_in_stable_order(db_session: Session) -> None:
    repo = ProjectRepository(db_session)
    first = repo.create({**_CREATE_DATA, "name": "First"})
    second = repo.create({**_CREATE_DATA, "name": "Second"})
    db_session.commit()

    projects = repo.list()

    assert [p.id for p in projects] == [first.id, second.id]


def test_update_applies_changes(db_session: Session) -> None:
    repo = ProjectRepository(db_session)
    project = repo.create(dict(_CREATE_DATA))
    db_session.commit()

    repo.update(project, {"name": "Renamed"})
    db_session.commit()

    assert project.name == "Renamed"


def test_delete_removes_project(db_session: Session) -> None:
    repo = ProjectRepository(db_session)
    project = repo.create(dict(_CREATE_DATA))
    db_session.commit()
    project_id = project.id

    repo.delete(project)
    db_session.commit()

    assert repo.get_by_id(project_id) is None


def test_create_does_not_commit(db_session: Session) -> None:
    repo = ProjectRepository(db_session)
    repo.create(dict(_CREATE_DATA))

    db_session.rollback()

    assert repo.list() == []
