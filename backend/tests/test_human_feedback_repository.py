"""HumanFeedbackRepository persistence behavior."""

from datetime import date

from sqlalchemy.orm import Session

from app.models.human_feedback import HumanFeedbackSourceMethod
from app.models.simulation_run import TaskOutcome
from app.models.variant import VariantKey
from app.repositories.human_feedback import HumanFeedbackRepository
from tests.experiment_helpers import seed_completed_experiment

_FEEDBACK_DATA = {
    "participant_label": "Participant 1",
    "variant_key": VariantKey.A,
    "task_outcome": TaskOutcome.COMPLETED,
    "clarity_score": 4,
    "perceived_value_score": 5,
    "adoption_intent_score": 4,
    "feedback_summary": "Completed the task with minimal confusion.",
    "positive_signals": [],
    "objections": [],
    "confusion_points": [],
    "feature_requests": [],
    "uncertainty_notes": [],
    "source_method": HumanFeedbackSourceMethod.USABILITY_TEST,
    "session_date": None,
}


def test_create_for_experiment_assigns_experiment_id(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)

    feedback = repo.create_for_experiment(experiment.id, dict(_FEEDBACK_DATA))

    assert feedback.id is not None
    assert feedback.experiment_id == experiment.id


def test_list_for_experiment_returns_only_that_experiments_feedback(db_session: Session) -> None:
    _project, experiment_a, _personas_a, _runs_a = seed_completed_experiment(db_session)
    _project_b, experiment_b, _personas_b, _runs_b = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)
    repo.create_for_experiment(experiment_a.id, dict(_FEEDBACK_DATA))
    repo.create_for_experiment(experiment_b.id, dict(_FEEDBACK_DATA))
    db_session.commit()

    items = repo.list_for_experiment(experiment_a.id)

    assert len(items) == 1
    assert items[0].experiment_id == experiment_a.id


def test_list_for_experiment_orders_by_session_date_then_created_at_then_id(
    db_session: Session,
) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)
    later_date = repo.create_for_experiment(
        experiment.id,
        {
            **_FEEDBACK_DATA,
            "participant_label": "Participant with later session date",
            "session_date": date(2026, 7, 20),
        },
    )
    earlier_date = repo.create_for_experiment(
        experiment.id,
        {
            **_FEEDBACK_DATA,
            "participant_label": "Participant with earlier session date",
            "variant_key": VariantKey.B,
            "session_date": date(2026, 7, 1),
        },
    )
    db_session.commit()

    items = repo.list_for_experiment(experiment.id)

    ids_by_session_date = [item.id for item in items if item.session_date is not None]
    assert ids_by_session_date == [earlier_date.id, later_date.id]


def test_get_by_experiment_and_id_returns_none_for_wrong_experiment(db_session: Session) -> None:
    _project, experiment_a, _personas_a, _runs_a = seed_completed_experiment(db_session)
    _project_b, experiment_b, _personas_b, _runs_b = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)
    feedback = repo.create_for_experiment(experiment_a.id, dict(_FEEDBACK_DATA))
    db_session.commit()

    assert repo.get_by_experiment_and_id(experiment_b.id, feedback.id) is None
    assert repo.get_by_experiment_and_id(experiment_a.id, feedback.id) is not None


def test_get_by_experiment_and_id_returns_none_when_missing(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)
    assert repo.get_by_experiment_and_id(experiment.id, 999) is None


def test_update_applies_changes(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)
    feedback = repo.create_for_experiment(experiment.id, dict(_FEEDBACK_DATA))
    db_session.commit()

    repo.update(feedback, {"feedback_summary": "Updated summary."})
    db_session.commit()

    assert feedback.feedback_summary == "Updated summary."


def test_delete_removes_human_feedback(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)
    feedback = repo.create_for_experiment(experiment.id, dict(_FEEDBACK_DATA))
    db_session.commit()
    feedback_id = feedback.id

    repo.delete(feedback)
    db_session.commit()

    assert repo.get_by_experiment_and_id(experiment.id, feedback_id) is None


def test_create_does_not_commit(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    repo = HumanFeedbackRepository(db_session)

    repo.create_for_experiment(experiment.id, dict(_FEEDBACK_DATA))

    db_session.rollback()
    assert repo.list_for_experiment(experiment.id) == []
