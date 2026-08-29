"""HumanFeedbackService: eligibility, CRUD, cross-project isolation,
duplicate prevention, and rollback behavior.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.experiment import ExperimentStatus
from app.models.human_feedback import HumanFeedbackSourceMethod
from app.repositories.human_feedback import HumanFeedbackRepository
from app.schemas.experiment import ExperimentCreate
from app.schemas.human_feedback import HumanFeedbackCreate, HumanFeedbackUpdate
from app.services.experiment import ExperimentService
from app.services.human_feedback import HumanFeedbackService
from tests.experiment_helpers import (
    experiment_create_payload,
    seed_completed_experiment,
    seed_project_with_personas,
)


def _create_payload(**overrides: object) -> HumanFeedbackCreate:
    defaults: dict[str, object] = {
        "participant_label": "Participant 1",
        "variant_key": "A",
        "source_method": HumanFeedbackSourceMethod.USABILITY_TEST,
        "task_outcome": "completed",
        "clarity_score": 4,
        "perceived_value_score": 5,
        "adoption_intent_score": 4,
        "feedback_summary": "Completed the task with minimal confusion.",
    }
    defaults.update(overrides)
    return HumanFeedbackCreate(**defaults)


def test_create_persists_feedback(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)

    feedback = HumanFeedbackService(db_session).create(project.id, experiment.id, _create_payload())

    assert feedback.id is not None
    assert feedback.experiment_id == experiment.id
    assert HumanFeedbackRepository(db_session).list_for_experiment(experiment.id) == [feedback]


def test_list_for_experiment(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    service.create(project.id, experiment.id, _create_payload())
    service.create(project.id, experiment.id, _create_payload(participant_label="Participant 2"))

    listed = service.list_for_experiment(project.id, experiment.id)
    assert len(listed) == 2


def test_get_retrieves_feedback(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    created = service.create(project.id, experiment.id, _create_payload())

    fetched = service.get(project.id, experiment.id, created.id)
    assert fetched.id == created.id


def test_update_changes_fields(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    created = service.create(project.id, experiment.id, _create_payload())

    updated = service.update(
        project.id,
        experiment.id,
        created.id,
        HumanFeedbackUpdate(feedback_summary="Updated after a follow-up call."),
    )

    assert updated.feedback_summary == "Updated after a follow-up call."


def test_delete_removes_feedback(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    created = service.create(project.id, experiment.id, _create_payload())

    service.delete(project.id, experiment.id, created.id)

    with pytest.raises(NotFoundError):
        service.get(project.id, experiment.id, created.id)


def test_create_project_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        HumanFeedbackService(db_session).create(999_999, 1, _create_payload())


def test_create_experiment_not_found(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    with pytest.raises(NotFoundError):
        HumanFeedbackService(db_session).create(project.id, 999_999, _create_payload())


def test_get_feedback_not_found(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    with pytest.raises(NotFoundError):
        HumanFeedbackService(db_session).get(project.id, experiment.id, 999_999)


def test_cross_project_experiment_returns_not_found(db_session: Session) -> None:
    _project_a, experiment_a, _personas_a, _runs_a = seed_completed_experiment(db_session)
    project_b, _experiment_b, _personas_b, _runs_b = seed_completed_experiment(db_session)

    with pytest.raises(NotFoundError):
        HumanFeedbackService(db_session).create(project_b.id, experiment_a.id, _create_payload())


def test_cross_project_feedback_returns_not_found(db_session: Session) -> None:
    project_a, experiment_a, _personas_a, _runs_a = seed_completed_experiment(db_session)
    project_b, experiment_b, _personas_b, _runs_b = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    created = service.create(project_a.id, experiment_a.id, _create_payload())

    with pytest.raises(NotFoundError):
        service.get(project_b.id, experiment_b.id, created.id)


@pytest.mark.parametrize(
    "status", [ExperimentStatus.DRAFT, ExperimentStatus.RUNNING, ExperimentStatus.FAILED]
)
def test_create_rejected_for_ineligible_status(
    db_session: Session, status: ExperimentStatus
) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = ExperimentService(db_session).create(
        project.id, ExperimentCreate(**experiment_create_payload([p.id for p in personas]))
    )
    experiment.status = status
    db_session.commit()

    with pytest.raises(ConflictError):
        HumanFeedbackService(db_session).create(project.id, experiment.id, _create_payload())

    assert HumanFeedbackRepository(db_session).list_for_experiment(experiment.id) == []


@pytest.mark.parametrize(
    "status", [ExperimentStatus.COMPLETED, ExperimentStatus.PARTIALLY_COMPLETED]
)
def test_create_accepted_for_eligible_status(db_session: Session, status: ExperimentStatus) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    experiment.status = status
    db_session.commit()

    feedback = HumanFeedbackService(db_session).create(project.id, experiment.id, _create_payload())
    assert feedback.id is not None


def test_edit_and_delete_allowed_regardless_of_status(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    created = service.create(project.id, experiment.id, _create_payload())

    experiment.status = ExperimentStatus.FAILED
    db_session.commit()

    updated = service.update(
        project.id, experiment.id, created.id, HumanFeedbackUpdate(feedback_summary="Edited.")
    )
    assert updated.feedback_summary == "Edited."

    service.delete(project.id, experiment.id, created.id)
    with pytest.raises(NotFoundError):
        service.get(project.id, experiment.id, created.id)


def test_duplicate_participant_and_variant_rejected_on_create(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    service.create(project.id, experiment.id, _create_payload())

    with pytest.raises(ConflictError):
        service.create(project.id, experiment.id, _create_payload())

    assert len(HumanFeedbackRepository(db_session).list_for_experiment(experiment.id)) == 1


def test_duplicate_participant_and_variant_rejected_on_update(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    service.create(project.id, experiment.id, _create_payload(participant_label="Participant 1"))
    second = service.create(
        project.id, experiment.id, _create_payload(participant_label="Participant 2")
    )

    with pytest.raises(ConflictError):
        service.update(
            project.id,
            experiment.id,
            second.id,
            HumanFeedbackUpdate(participant_label="Participant 1"),
        )


def test_rollback_on_duplicate_create_leaves_no_partial_row(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    service = HumanFeedbackService(db_session)
    service.create(project.id, experiment.id, _create_payload())

    with pytest.raises(ConflictError):
        service.create(project.id, experiment.id, _create_payload())

    remaining = HumanFeedbackRepository(db_session).list_for_experiment(experiment.id)
    assert len(remaining) == 1
    assert remaining[0].participant_label == "Participant 1"
