"""Deterministic Insight-generation context builder.

Verifies the assembled context is byte-identical for the same persisted
state, includes exactly the allowed input surface (objective, hypothesis,
both variant definitions, deterministic metrics, completed run IDs, and
each completed run's structured output), excludes anything not on that
list, and enforces `INSIGHT_CONTEXT_CHAR_LIMIT` before any provider call.
"""

import pytest
from sqlalchemy.orm import Session

from app.llm.insight_context import (
    INSIGHT_CONTEXT_CHAR_LIMIT,
    InsightContextTooLargeError,
    build_insight_context,
)
from app.models.variant import VariantKey
from app.services.analytics import ExperimentAnalyticsService
from tests.experiment_helpers import seed_completed_experiment


def _variants(experiment):
    by_key = {variant.key: variant for variant in experiment.variants}
    return by_key[VariantKey.A], by_key[VariantKey.B]


def test_context_is_deterministic_across_calls(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]

    context_1 = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=completed_runs,
    )
    context_2 = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=list(reversed(completed_runs)),
    )
    assert context_1 == context_2


def test_context_includes_objective_and_hypothesis(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(db_session)
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]

    context = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=completed_runs,
    )
    assert experiment.objective in context
    assert experiment.hypothesis in context


def test_context_includes_both_variant_definitions(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(db_session)
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]

    context = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=completed_runs,
    )
    assert variant_a.name in context
    assert variant_a.description in context
    assert variant_b.name in context
    assert variant_b.description in context


def test_context_includes_deterministic_metrics(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(db_session)
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]

    context = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=completed_runs,
    )
    assert "DETERMINISTIC METRICS" in context
    assert "task_completion_rate" in context


def test_context_includes_only_completed_runs(db_session: Session) -> None:
    from app.llm.exceptions import LLMTimeoutError
    from tests.fakes import make_simulation_call_result

    project, experiment, _personas, runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[make_simulation_call_result(), LLMTimeoutError("timed out")],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]
    failed_runs = [run for run in runs if run.status.value == "failed"]
    assert len(completed_runs) == 1
    assert len(failed_runs) == 1

    context = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=completed_runs,
    )
    for run in completed_runs:
        assert f"run_id={run.id}" in context
    for run in failed_runs:
        assert f"run_id={run.id}" not in context


def test_context_includes_run_ids_and_evidence_ids(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(db_session)
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]

    context = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=completed_runs,
    )
    assert "Allowed run_id values" in context
    assert "evidence_item_id=1" in context


def test_context_excludes_raw_provider_output_markers(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(db_session)
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]

    context = build_insight_context(
        experiment=experiment,
        variant_a=variant_a,
        variant_b=variant_b,
        analytics=analytics,
        completed_runs=completed_runs,
    )
    assert "api_key" not in context.lower()
    assert "sk-" not in context


def test_context_limit_enforced_without_silent_truncation(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(db_session)
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    variant_a, variant_b = _variants(experiment)
    completed_runs = [run for run in runs if run.status.value == "completed"]

    with pytest.raises(InsightContextTooLargeError):
        build_insight_context(
            experiment=experiment,
            variant_a=variant_a,
            variant_b=variant_b,
            analytics=analytics,
            completed_runs=completed_runs,
            char_limit=10,
        )


def test_default_char_limit_is_thirty_thousand() -> None:
    assert INSIGHT_CONTEXT_CHAR_LIMIT == 30_000
