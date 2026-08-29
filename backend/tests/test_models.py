"""SQLAlchemy model behavior: defaults, timestamps, relationships, cascade delete."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.evidence_item import EvidenceItem, EvidenceType
from app.models.project import Project, ProjectStatus


def _make_project(**overrides: object) -> Project:
    defaults = {
        "name": "Portfolio Discovery Tool",
        "problem_statement": "Teams decide on intuition alone.",
        "target_user": "Early-stage product managers.",
        "product_hypothesis": "Evidence-grounded personas surface weak assumptions.",
        "success_metric": "Time to a decision memo.",
        "assumptions": ["Users have existing evidence."],
    }
    defaults.update(overrides)
    return Project(**defaults)


def test_project_default_status_is_draft(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    assert project.status == ProjectStatus.DRAFT


def test_project_timestamps_default_to_utc_now(db_session: Session) -> None:
    # Checked before commit: SQLite has no native timezone-aware datetime
    # type, so a committed-and-reloaded value round-trips as naive. The
    # Python-side default is what actually guarantees UTC, so that's what
    # this asserts against.
    project = _make_project()
    db_session.add(project)
    db_session.flush()

    assert project.created_at.tzinfo is not None
    assert project.created_at.utcoffset() == timedelta(0)
    assert project.updated_at.tzinfo is not None
    assert project.updated_at.utcoffset() == timedelta(0)


def test_updating_project_updates_updated_at(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()
    original_updated_at = project.updated_at

    project.name = "Renamed Discovery Tool"
    db_session.commit()

    assert project.updated_at >= original_updated_at


def test_project_evidence_items_relationship(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    evidence = EvidenceItem(
        project_id=project.id,
        evidence_type=EvidenceType.INTERVIEW_NOTE,
        title="Interview with early adopter",
        content="They struggled to understand the value prop.",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(project)

    assert len(project.evidence_items) == 1
    assert project.evidence_items[0].id == evidence.id
    assert evidence.project.id == project.id


def test_deleting_project_cascades_to_evidence_items(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    evidence = EvidenceItem(
        project_id=project.id,
        evidence_type=EvidenceType.SUPPORT_TICKET,
        title="Support ticket",
        content="Customer reported a confusing onboarding flow.",
    )
    db_session.add(evidence)
    db_session.commit()
    evidence_id = evidence.id

    db_session.delete(project)
    db_session.commit()

    assert db_session.get(EvidenceItem, evidence_id) is None
