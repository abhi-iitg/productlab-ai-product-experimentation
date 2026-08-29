"""ExperimentService: CRUD, draft-only editing, and creation-time validation."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidRequestError, NotFoundError
from app.models.experiment import ExperimentStatus
from app.schemas.experiment import ExperimentCreate, ExperimentUpdate
from app.services.experiment import ExperimentService
from tests.experiment_helpers import experiment_create_payload, seed_project_with_personas


def test_create_experiment(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)

    experiment = service.create(
        project.id, ExperimentCreate(**experiment_create_payload([personas[0].id]))
    )

    assert experiment.id is not None
    assert experiment.status == ExperimentStatus.DRAFT
    assert experiment.persona_ids == [personas[0].id]
    assert {v.key.value for v in experiment.variants} == {"A", "B"}


def test_list_experiments_for_project(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    service.create(project.id, ExperimentCreate(**experiment_create_payload([personas[0].id])))
    service.create(
        project.id,
        ExperimentCreate(**experiment_create_payload([personas[0].id], name="Second experiment")),
    )

    experiments = service.list_for_project(project.id)

    assert len(experiments) == 2


def test_get_experiment(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    created = service.create(
        project.id, ExperimentCreate(**experiment_create_payload([personas[0].id]))
    )

    fetched = service.get(project.id, created.id)

    assert fetched.id == created.id


def test_create_raises_when_project_not_found(db_session: Session) -> None:
    service = ExperimentService(db_session)
    with pytest.raises(NotFoundError):
        service.create(999, ExperimentCreate(**experiment_create_payload([1])))


def test_get_raises_when_experiment_not_found(db_session: Session) -> None:
    project, _evidence, _personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    with pytest.raises(NotFoundError):
        service.get(project.id, 999)


def test_create_raises_when_persona_not_found(db_session: Session) -> None:
    project, _evidence, _personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    with pytest.raises(InvalidRequestError):
        service.create(project.id, ExperimentCreate(**experiment_create_payload([999])))


def test_create_rejects_persona_from_another_project(db_session: Session) -> None:
    project_a, _evidence_a, personas_a = seed_project_with_personas(db_session)
    project_b, _evidence_b, _personas_b = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)

    with pytest.raises(InvalidRequestError):
        service.create(
            project_b.id, ExperimentCreate(**experiment_create_payload([personas_a[0].id]))
        )


def test_create_rejects_calculated_run_count_over_thirty(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session, persona_count=6)
    service = ExperimentService(db_session)
    payload = experiment_create_payload([p.id for p in personas], repeat_count=3)

    # 6 personas x 2 variants x 3 repeats = 36 > 30.
    with pytest.raises(InvalidRequestError):
        service.create(project.id, ExperimentCreate(**payload))


def test_update_draft_experiment(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    experiment = service.create(
        project.id, ExperimentCreate(**experiment_create_payload([personas[0].id]))
    )

    updated = service.update(
        project.id, experiment.id, ExperimentUpdate(name="Updated experiment name")
    )

    assert updated.name == "Updated experiment name"


def test_delete_draft_experiment(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    experiment = service.create(
        project.id, ExperimentCreate(**experiment_create_payload([personas[0].id]))
    )

    service.delete(project.id, experiment.id)

    with pytest.raises(NotFoundError):
        service.get(project.id, experiment.id)


def test_update_after_execution_starts_is_rejected(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    experiment = service.create(
        project.id, ExperimentCreate(**experiment_create_payload([personas[0].id]))
    )
    experiment.status = ExperimentStatus.RUNNING
    db_session.commit()

    with pytest.raises(ConflictError):
        service.update(project.id, experiment.id, ExperimentUpdate(name="Should not apply"))


def test_delete_after_execution_starts_is_rejected(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    experiment = service.create(
        project.id, ExperimentCreate(**experiment_create_payload([personas[0].id]))
    )
    experiment.status = ExperimentStatus.COMPLETED
    db_session.commit()

    with pytest.raises(ConflictError):
        service.delete(project.id, experiment.id)


def test_cross_project_experiment_access_returns_not_found(db_session: Session) -> None:
    project_a, _evidence_a, personas_a = seed_project_with_personas(db_session)
    project_b, _evidence_b, _personas_b = seed_project_with_personas(db_session)
    service = ExperimentService(db_session)
    experiment = service.create(
        project_a.id, ExperimentCreate(**experiment_create_payload([personas_a[0].id]))
    )

    with pytest.raises(NotFoundError):
        service.get(project_b.id, experiment.id)
