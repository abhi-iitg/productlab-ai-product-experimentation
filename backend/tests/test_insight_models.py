"""SQLAlchemy Insight model behavior: defaults, timestamps, relationships,
cascade delete, and the unique constraint on (experiment_id, title,
category, variant_scope).
"""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.insight import Insight, InsightCategory, VariantScope
from app.models.persona import ConfidenceLevel
from tests.experiment_helpers import seed_completed_experiment


def _make_insight(experiment_id: int, **overrides: object) -> Insight:
    defaults: dict[str, object] = {
        "experiment_id": experiment_id,
        "category": InsightCategory.STRENGTH,
        "variant_scope": VariantScope.BOTH,
        "title": "Clear value proposition",
        "summary": "Personas consistently understood the value proposition.",
        "frequency": 2,
        "persona_count": 2,
        "supporting_run_ids": [1, 2],
        "supporting_evidence_ids": [1],
        "confidence_level": ConfidenceLevel.MEDIUM,
        "prompt_version": "insight-v1",
        "model_name": "fake-insight-model-v1",
    }
    defaults.update(overrides)
    return Insight(**defaults)


def test_insight_persists_with_all_fields(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    insight = _make_insight(experiment.id)
    db_session.add(insight)
    db_session.commit()

    assert insight.id is not None
    assert insight.category == InsightCategory.STRENGTH
    assert insight.variant_scope == VariantScope.BOTH
    assert insight.confidence_level == ConfidenceLevel.MEDIUM
    assert insight.prompt_version == "insight-v1"
    assert insight.supporting_run_ids == [1, 2]
    assert insight.supporting_evidence_ids == [1]


def test_insight_timestamps_default_to_utc_now(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    insight = _make_insight(experiment.id)
    db_session.add(insight)
    db_session.flush()

    assert insight.created_at.tzinfo is not None
    assert insight.created_at.utcoffset() == timedelta(0)


def test_experiment_insights_relationship(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    insight = _make_insight(experiment.id)
    db_session.add(insight)
    db_session.commit()
    db_session.refresh(experiment)

    assert len(experiment.insights) == 1
    assert experiment.insights[0].id == insight.id
    assert insight.experiment.id == experiment.id


def test_deleting_experiment_cascades_to_insights(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    insight = _make_insight(experiment.id)
    db_session.add(insight)
    db_session.commit()
    insight_id = insight.id

    db_session.delete(experiment)
    db_session.commit()

    assert db_session.get(Insight, insight_id) is None


def test_insight_unique_constraint_per_title_category_variant(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    db_session.add(_make_insight(experiment.id))
    db_session.commit()

    db_session.add(_make_insight(experiment.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_insight_different_variant_scope_is_not_a_duplicate(db_session: Session) -> None:
    _project, experiment, _personas, _runs = seed_completed_experiment(db_session)
    db_session.add(_make_insight(experiment.id, variant_scope=VariantScope.A))
    db_session.add(_make_insight(experiment.id, variant_scope=VariantScope.B))
    db_session.commit()  # must not raise

    assert len(experiment.insights) == 2
