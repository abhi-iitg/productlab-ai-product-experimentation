"""SQLAlchemy DecisionMemo model behavior: defaults, timestamps,
relationships, cascade delete, and the one-memo-per-experiment uniqueness
constraint.
"""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.decision_memo import DecisionMemo, Recommendation
from tests.experiment_helpers import seed_completed_experiment

_REAL_USER_TEST = {
    "objective": "Validate whether real users complete setup unaided.",
    "target_participants": ["5-8 early-stage product managers."],
    "method": "Moderated usability test.",
    "sample_size_rationale": "Sufficient to surface major usability blockers.",
    "tasks_or_questions": ["Complete setup unaided."],
    "success_metrics": ["Setup completion rate."],
    "stopping_rule": "Stop after 5 sessions if the same blocker recurs.",
}


def _make_memo(experiment_id: int, **overrides: object) -> DecisionMemo:
    defaults: dict[str, object] = {
        "experiment_id": experiment_id,
        "recommendation": Recommendation.PROCEED,
        "executive_summary": "Signal is strong; recommend real-user validation next.",
        "supporting_findings": ["Personas understood the value proposition."],
        "weakest_assumptions": ["Assumes unaided discovery."],
        "recommended_product_changes": ["Add an inline hint."],
        "risks": ["Evidence library is thin."],
        "uncertain_conclusions": ["Moderate confidence on adoption intent."],
        "recommended_success_metrics": ["Setup completion rate."],
        "real_user_test": _REAL_USER_TEST,
        "supporting_insight_ids": [1, 2],
        "prompt_version": "decision-v1",
        "model_name": "fake-decision-model-v1",
    }
    defaults.update(overrides)
    return DecisionMemo(**defaults)


def test_memo_persists_with_all_fields(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    memo = _make_memo(experiment.id)
    db_session.add(memo)
    db_session.commit()

    assert memo.id is not None
    assert memo.recommendation == Recommendation.PROCEED
    assert memo.real_user_test == _REAL_USER_TEST
    assert memo.supporting_insight_ids == [1, 2]


def test_memo_timestamps_default_to_utc_now(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    memo = _make_memo(experiment.id)
    db_session.add(memo)
    db_session.flush()

    assert memo.created_at.tzinfo is not None
    assert memo.created_at.utcoffset() == timedelta(0)
    assert memo.updated_at.tzinfo is not None


def test_updating_memo_updates_updated_at(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    memo = _make_memo(experiment.id)
    db_session.add(memo)
    db_session.commit()
    original_updated_at = memo.updated_at

    memo.executive_summary = "Revised summary."
    db_session.commit()

    assert memo.updated_at >= original_updated_at


def test_experiment_decision_memo_relationship(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    memo = _make_memo(experiment.id)
    db_session.add(memo)
    db_session.commit()
    db_session.refresh(experiment)

    assert experiment.decision_memo.id == memo.id
    assert memo.experiment.id == experiment.id


def test_deleting_experiment_cascades_to_decision_memo(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    memo = _make_memo(experiment.id)
    db_session.add(memo)
    db_session.commit()
    memo_id = memo.id

    db_session.delete(experiment)
    db_session.commit()

    assert db_session.get(DecisionMemo, memo_id) is None


def test_one_memo_per_experiment_uniqueness(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    db_session.add(_make_memo(experiment.id))
    db_session.commit()

    db_session.add(_make_memo(experiment.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
