"""SQLAlchemy Persona model behavior: defaults, timestamps, relationships, cascade delete."""

from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.persona import ConfidenceLevel, Persona
from app.models.project import Project


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


def _make_persona(project_id: int, **overrides: object) -> Persona:
    defaults: dict[str, object] = {
        "project_id": project_id,
        "name": "Alex the Adopter",
        "segment_label": "Early Adopter",
        "summary": "An early adopter evaluating the product.",
        "goals": ["Understand the value quickly."],
        "pain_points": ["Confusing onboarding."],
        "constraints": ["Limited evaluation time."],
        "behaviors": ["Reads reviews before adopting tools."],
        "evidence_references": [
            {"evidence_item_id": 1, "supported_claims": ["Struggled with onboarding."]}
        ],
        "unsupported_assumptions": ["Likely price-sensitive."],
        "confidence_level": ConfidenceLevel.MEDIUM,
        "prompt_version": "persona-v1",
        "model_name": "fake-model-v1",
    }
    defaults.update(overrides)
    return Persona(**defaults)


def test_persona_persists_with_all_fields(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    persona = _make_persona(project.id)
    db_session.add(persona)
    db_session.commit()

    assert persona.id is not None
    assert persona.confidence_level == ConfidenceLevel.MEDIUM
    assert persona.prompt_version == "persona-v1"
    assert persona.model_name == "fake-model-v1"
    assert persona.evidence_references == [
        {"evidence_item_id": 1, "supported_claims": ["Struggled with onboarding."]}
    ]


def test_persona_timestamps_default_to_utc_now(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    persona = _make_persona(project.id)
    db_session.add(persona)
    db_session.flush()

    assert persona.created_at.tzinfo is not None
    assert persona.created_at.utcoffset() == timedelta(0)
    assert persona.updated_at.tzinfo is not None
    assert persona.updated_at.utcoffset() == timedelta(0)


def test_updating_persona_updates_updated_at(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    persona = _make_persona(project.id)
    db_session.add(persona)
    db_session.commit()
    original_updated_at = persona.updated_at

    persona.summary = "Updated summary."
    db_session.commit()

    assert persona.updated_at >= original_updated_at


def test_project_personas_relationship(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    persona = _make_persona(project.id)
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(project)

    assert len(project.personas) == 1
    assert project.personas[0].id == persona.id
    assert persona.project.id == project.id


def test_deleting_project_cascades_to_personas(db_session: Session) -> None:
    project = _make_project()
    db_session.add(project)
    db_session.commit()

    persona = _make_persona(project.id)
    db_session.add(persona)
    db_session.commit()
    persona_id = persona.id

    db_session.delete(project)
    db_session.commit()

    assert db_session.get(Persona, persona_id) is None
