"""SQLAlchemy Experiment/Variant/SimulationRun model behavior."""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.experiment import Experiment, ExperimentStatus
from app.models.simulation_run import SimulationRun, SimulationRunStatus
from app.models.variant import Variant, VariantKey
from tests.experiment_helpers import experiment_create_payload, seed_project_with_personas


def _make_experiment(project_id: int, persona_ids: list[int], **overrides: object) -> Experiment:
    defaults: dict[str, object] = {
        "project_id": project_id,
        "name": "Onboarding concept comparison",
        "objective": "Compare two onboarding approaches",
        "hypothesis": "A guided setup will improve clarity",
        "scenario": "Evaluate the onboarding flow.",
        "evaluation_criteria": ["Clarity", "Adoption intent"],
        "repeat_count": 1,
    }
    defaults.update(overrides)
    return Experiment(**defaults)


def test_experiment_default_status_is_draft(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = _make_experiment(project.id, [personas[0].id])
    experiment.variants = [
        Variant(key=VariantKey.A, name="Variant A", description="A description."),
        Variant(key=VariantKey.B, name="Variant B", description="B description."),
    ]
    experiment.personas = personas
    db_session.add(experiment)
    db_session.commit()

    assert experiment.status == ExperimentStatus.DRAFT
    assert experiment.persona_ids == [personas[0].id]


def test_experiment_timestamps_default_to_utc_now(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = _make_experiment(project.id, [personas[0].id])
    db_session.add(experiment)
    db_session.flush()

    assert experiment.created_at.tzinfo is not None
    assert experiment.created_at.utcoffset() == timedelta(0)
    assert experiment.updated_at.tzinfo is not None
    assert experiment.started_at is None
    assert experiment.completed_at is None


def test_updating_experiment_updates_updated_at(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = _make_experiment(project.id, [personas[0].id])
    db_session.add(experiment)
    db_session.commit()
    original_updated_at = experiment.updated_at

    experiment.name = "Renamed experiment"
    db_session.commit()

    assert experiment.updated_at >= original_updated_at


def test_variant_key_uniqueness_per_experiment(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = _make_experiment(project.id, [personas[0].id])
    experiment.variants = [
        Variant(key=VariantKey.A, name="Variant A", description="A description."),
        Variant(key=VariantKey.A, name="Duplicate A", description="Also A."),
    ]
    db_session.add(experiment)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_project_cascades_to_experiments_and_variants(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = _make_experiment(project.id, [personas[0].id])
    experiment.variants = [
        Variant(key=VariantKey.A, name="Variant A", description="A description."),
        Variant(key=VariantKey.B, name="Variant B", description="B description."),
    ]
    db_session.add(experiment)
    db_session.commit()
    experiment_id = experiment.id
    variant_id = experiment.variants[0].id

    db_session.delete(project)
    db_session.commit()

    assert db_session.get(Experiment, experiment_id) is None
    assert db_session.get(Variant, variant_id) is None


def test_deleting_experiment_cascades_to_runs(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = _make_experiment(project.id, [personas[0].id])
    variant_a = Variant(key=VariantKey.A, name="Variant A", description="A description.")
    experiment.variants = [variant_a]
    db_session.add(experiment)
    db_session.commit()

    run = SimulationRun(
        experiment_id=experiment.id,
        variant_id=variant_a.id,
        persona_id=personas[0].id,
        repetition_index=0,
        status=SimulationRunStatus.FAILED,
        prompt_version="simulation-v1",
        model_name="fake-simulation-model-v1",
        failure_type=None,
        failure_message=None,
    )
    db_session.add(run)
    db_session.commit()
    run_id = run.id

    db_session.delete(experiment)
    db_session.commit()

    assert db_session.get(SimulationRun, run_id) is None


def test_simulation_run_matrix_uniqueness_constraint(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session)
    experiment = _make_experiment(project.id, [personas[0].id])
    variant_a = Variant(key=VariantKey.A, name="Variant A", description="A description.")
    experiment.variants = [variant_a]
    db_session.add(experiment)
    db_session.commit()

    run_kwargs = {
        "experiment_id": experiment.id,
        "variant_id": variant_a.id,
        "persona_id": personas[0].id,
        "repetition_index": 0,
        "status": SimulationRunStatus.FAILED,
        "prompt_version": "simulation-v1",
        "model_name": "fake-simulation-model-v1",
    }
    db_session.add(SimulationRun(**run_kwargs))
    db_session.commit()

    db_session.add(SimulationRun(**run_kwargs))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_experiment_personas_relationship_is_reproducible(db_session: Session) -> None:
    project, _evidence, personas = seed_project_with_personas(db_session, persona_count=2)
    experiment = _make_experiment(project.id, [p.id for p in personas])
    experiment.personas = personas
    db_session.add(experiment)
    db_session.commit()
    db_session.refresh(experiment)

    assert sorted(experiment.persona_ids) == sorted(p.id for p in personas)


def test_experiment_create_payload_helper_matches_schema_shape() -> None:
    # Sanity check on the shared test payload builder used across API tests.
    payload = experiment_create_payload([1, 2])
    assert payload["persona_ids"] == [1, 2]
    assert {v["key"] for v in payload["variants"]} == {"A", "B"}
