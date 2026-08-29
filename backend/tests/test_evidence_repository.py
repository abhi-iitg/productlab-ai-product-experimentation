"""EvidenceRepository persistence behavior."""

from sqlalchemy.orm import Session

from app.models.evidence_item import EvidenceType
from app.repositories.evidence import EvidenceRepository
from app.repositories.project import ProjectRepository

_PROJECT_DATA = {
    "name": "Portfolio Discovery Tool",
    "problem_statement": "Teams decide on intuition alone.",
    "target_user": "Early-stage product managers.",
    "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
    "success_metric": "Time to a decision memo.",
    "assumptions": [],
}

_EVIDENCE_DATA = {
    "evidence_type": EvidenceType.INTERVIEW_NOTE,
    "title": "Interview with early adopter",
    "content": "They struggled with onboarding.",
    "source_label": "Zoom call, 2026-06-01",
}


def _create_project(db_session: Session) -> int:
    project = ProjectRepository(db_session).create(dict(_PROJECT_DATA))
    db_session.commit()
    return project.id


def test_create_for_project_assigns_project_id(db_session: Session) -> None:
    project_id = _create_project(db_session)
    repo = EvidenceRepository(db_session)

    evidence = repo.create_for_project(project_id, dict(_EVIDENCE_DATA))

    assert evidence.id is not None
    assert evidence.project_id == project_id


def test_list_for_project_returns_only_that_projects_evidence(db_session: Session) -> None:
    project_a = _create_project(db_session)
    project_b = _create_project(db_session)
    repo = EvidenceRepository(db_session)
    repo.create_for_project(project_a, dict(_EVIDENCE_DATA))
    repo.create_for_project(project_b, dict(_EVIDENCE_DATA))
    db_session.commit()

    items = repo.list_for_project(project_a)

    assert len(items) == 1
    assert items[0].project_id == project_a


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = EvidenceRepository(db_session)
    assert repo.get_by_id(999) is None


def test_update_applies_changes(db_session: Session) -> None:
    project_id = _create_project(db_session)
    repo = EvidenceRepository(db_session)
    evidence = repo.create_for_project(project_id, dict(_EVIDENCE_DATA))
    db_session.commit()

    repo.update(evidence, {"title": "Updated title"})
    db_session.commit()

    assert evidence.title == "Updated title"


def test_delete_removes_evidence_item(db_session: Session) -> None:
    project_id = _create_project(db_session)
    repo = EvidenceRepository(db_session)
    evidence = repo.create_for_project(project_id, dict(_EVIDENCE_DATA))
    db_session.commit()
    evidence_id = evidence.id

    repo.delete(evidence)
    db_session.commit()

    assert repo.get_by_id(evidence_id) is None
