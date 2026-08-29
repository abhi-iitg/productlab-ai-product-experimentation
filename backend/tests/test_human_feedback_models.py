"""SQLAlchemy HumanFeedback model behavior: defaults, timestamps,
relationships, cascade delete, and the unique constraint on
(experiment_id, participant_label, variant_key).
"""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.human_feedback import HumanFeedback, HumanFeedbackSourceMethod
from app.models.simulation_run import TaskOutcome
from app.models.variant import VariantKey
from tests.experiment_helpers import seed_completed_experiment


def _make_human_feedback(experiment_id: int, **overrides: object) -> HumanFeedback:
    defaults: dict[str, object] = {
        "experiment_id": experiment_id,
        "participant_label": "Participant 1",
        "variant_key": VariantKey.A,
        "task_outcome": TaskOutcome.COMPLETED,
        "clarity_score": 4,
        "perceived_value_score": 5,
        "adoption_intent_score": 4,
        "feedback_summary": "The participant completed the task with minimal confusion.",
        "positive_signals": ["Liked the guided steps"],
        "objections": [],
        "confusion_points": [],
        "feature_requests": ["Would like a progress indicator"],
        "uncertainty_notes": [],
        "source_method": HumanFeedbackSourceMethod.USABILITY_TEST,
        "session_date": None,
    }
    defaults.update(overrides)
    return HumanFeedback(**defaults)


def test_human_feedback_persists_with_all_fields(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    feedback = _make_human_feedback(experiment.id)
    db_session.add(feedback)
    db_session.commit()

    assert feedback.id is not None
    assert feedback.participant_label == "Participant 1"
    assert feedback.variant_key == VariantKey.A
    assert feedback.task_outcome == TaskOutcome.COMPLETED
    assert feedback.source_method == HumanFeedbackSourceMethod.USABILITY_TEST
    assert feedback.positive_signals == ["Liked the guided steps"]
    assert feedback.session_date is None


def test_human_feedback_timestamps_default_to_utc_now(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    feedback = _make_human_feedback(experiment.id)
    db_session.add(feedback)
    db_session.flush()

    assert feedback.created_at.tzinfo is not None
    assert feedback.created_at.utcoffset() == timedelta(0)
    assert feedback.updated_at.tzinfo is not None
    assert feedback.updated_at.utcoffset() == timedelta(0)


def test_human_feedback_updated_at_changes_on_edit(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    feedback = _make_human_feedback(experiment.id)
    db_session.add(feedback)
    db_session.commit()
    original_updated_at = feedback.updated_at

    feedback.feedback_summary = "Updated summary after a follow-up conversation."
    db_session.commit()

    assert feedback.updated_at >= original_updated_at


def test_experiment_human_feedback_relationship(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    feedback = _make_human_feedback(experiment.id)
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(experiment)

    assert len(experiment.human_feedback) == 1
    assert experiment.human_feedback[0].id == feedback.id
    assert feedback.experiment.id == experiment.id


def test_deleting_experiment_cascades_to_human_feedback(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    feedback = _make_human_feedback(experiment.id)
    db_session.add(feedback)
    db_session.commit()
    feedback_id = feedback.id

    db_session.delete(experiment)
    db_session.commit()

    assert db_session.get(HumanFeedback, feedback_id) is None


def test_human_feedback_unique_constraint_per_participant_and_variant(
    db_session: Session,
) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    db_session.add(_make_human_feedback(experiment.id))
    db_session.commit()

    db_session.add(_make_human_feedback(experiment.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_human_feedback_different_variant_key_is_not_a_duplicate(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    db_session.add(_make_human_feedback(experiment.id, variant_key=VariantKey.A))
    db_session.add(_make_human_feedback(experiment.id, variant_key=VariantKey.B))
    db_session.commit()  # must not raise

    assert len(experiment.human_feedback) == 2


def test_human_feedback_different_participant_label_is_not_a_duplicate(
    db_session: Session,
) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    db_session.add(_make_human_feedback(experiment.id, participant_label="Participant 1"))
    db_session.add(_make_human_feedback(experiment.id, participant_label="Participant 2"))
    db_session.commit()  # must not raise

    assert len(experiment.human_feedback) == 2
