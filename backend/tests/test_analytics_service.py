"""ExperimentAnalyticsService: deterministic aggregation over persisted
SimulationRuns — coverage, per-variant metrics, theme counts, evidence
coverage, failure breakdown, persona disagreement, and data-quality
warnings/flags.

No provider or network calls anywhere in this file — analytics reads only
already-persisted, already-executed SimulationRuns.
"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ConflictError
from app.llm.exceptions import LLMTimeoutError
from app.models.experiment import ExperimentStatus
from app.models.simulation_run import FailureType, TaskOutcome
from app.models.variant import VariantKey
from app.schemas.experiment import ExperimentCreate, ExperimentExecuteRequest
from app.services.analytics import ExperimentAnalyticsService
from app.services.experiment import ExperimentService
from app.services.experiment_execution import ExperimentExecutionService
from tests.experiment_helpers import (
    experiment_create_payload,
    seed_completed_experiment,
    seed_project_with_personas,
)
from tests.fakes import FakeSimulationProvider, make_simulation_call_result


def test_completed_experiment_metrics(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.experiment_id == experiment.id
    assert analytics.experiment_status == ExperimentStatus.COMPLETED
    assert analytics.coverage.expected_runs == 4
    assert analytics.coverage.total_persisted_runs == len(runs) == 4
    assert analytics.coverage.completed_runs == 4
    assert analytics.coverage.failed_runs == 0
    assert analytics.coverage.completion_rate == 1.0
    assert analytics.coverage.represented_persona_count == 2
    assert analytics.data_quality_warnings == []


def test_partially_completed_experiment_metrics(db_session: Session) -> None:
    project, experiment, _personas, runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[make_simulation_call_result(), LLMTimeoutError("timed out")],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.experiment_status == ExperimentStatus.PARTIALLY_COMPLETED
    assert analytics.coverage.completed_runs == 1
    assert analytics.coverage.failed_runs == 1
    assert analytics.coverage.total_persisted_runs == len(runs) == 2


def test_per_variant_averages_and_task_outcome_distribution(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(
                clarity_score=5,
                perceived_value_score=5,
                adoption_intent_score=5,
                task_outcome=TaskOutcome.COMPLETED,
                latency_ms=100,
                input_tokens=10,
                output_tokens=20,
            ),
            make_simulation_call_result(
                clarity_score=1,
                perceived_value_score=2,
                adoption_intent_score=3,
                task_outcome=TaskOutcome.PARTIALLY_COMPLETED,
                latency_ms=300,
                input_tokens=30,
                output_tokens=40,
            ),
        ],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    variant_a, variant_b = analytics.variant_metrics
    assert variant_a.variant_key == VariantKey.A
    assert variant_b.variant_key == VariantKey.B

    assert variant_a.average_clarity_score == 5.0
    assert variant_a.average_perceived_value_score == 5.0
    assert variant_a.average_adoption_intent_score == 5.0
    assert variant_a.average_latency_ms == 100.0
    assert variant_a.total_input_tokens == 10
    assert variant_a.total_output_tokens == 20
    assert variant_a.task_outcome_distribution.completed == 1
    assert variant_a.task_completion_rate == 1.0

    assert variant_b.average_clarity_score == 1.0
    assert variant_b.task_outcome_distribution.partially_completed == 1
    assert variant_b.task_completion_rate == 0.0


def test_deterministic_theme_counts(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[
            make_simulation_call_result(
                positive_signals=["Loved the flow.", "Fast to complete."],
                objections=["Too expensive."],
            ),
            make_simulation_call_result(
                confusion_points=["Unclear pricing."],
                feature_requests=["Add dark mode."],
                uncertainty_notes=["Not sure this fits my workflow."],
            ),
        ],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    theme_a = analytics.deterministic_theme_counts[VariantKey.A]
    theme_b = analytics.deterministic_theme_counts[VariantKey.B]
    assert theme_a.positive_signals == 2
    assert theme_a.objections == 1
    assert theme_a.confusion_points == 0
    assert theme_b.confusion_points == 1
    assert theme_b.feature_requests == 1
    assert theme_b.uncertainty_notes == 1


def test_failure_breakdown_by_safe_category(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[LLMTimeoutError("timed out"), make_simulation_call_result()],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.failure_breakdown.total_failed_runs == 1
    assert analytics.failure_breakdown.counts_by_category[FailureType.TIMEOUT] == 1
    assert analytics.failure_breakdown.counts_by_category[FailureType.RATE_LIMIT] == 0
    # every FailureType is present for stable, predictable response shape
    assert set(analytics.failure_breakdown.counts_by_category.keys()) == set(FailureType)


def test_evidence_coverage(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session, persona_count=1, repeat_count=1
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.evidence_coverage.completed_runs_total == 2
    assert analytics.evidence_coverage.completed_runs_with_evidence == 2
    assert analytics.evidence_coverage.evidence_citation_rate == 1.0
    assert analytics.evidence_coverage.unique_cited_evidence_ids == [1]


def test_token_and_cost_totals(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        result=make_simulation_call_result(input_tokens=100, output_tokens=200),
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    for variant in analytics.variant_metrics:
        assert variant.total_input_tokens == 100
        assert variant.total_output_tokens == 200


def test_cost_totals_computed_when_all_runs_have_cost(db_session: Session) -> None:
    project, evidence, personas = seed_project_with_personas(db_session, persona_count=1)
    experiment = ExperimentService(db_session).create(
        project.id,
        ExperimentCreate(**experiment_create_payload([p.id for p in personas], repeat_count=1)),
    )
    provider = FakeSimulationProvider(
        result=make_simulation_call_result(input_tokens=1_000_000, output_tokens=1_000_000)
    )
    settings = Settings(
        _env_file=None,
        OPENAI_INPUT_COST_PER_1M=Decimal("5"),
        OPENAI_OUTPUT_COST_PER_1M=Decimal("15"),
    )
    ExperimentExecutionService(db_session, provider, settings=settings).execute(
        project.id, experiment.id, ExperimentExecuteRequest(confirm_execution=True)
    )

    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)
    for variant in analytics.variant_metrics:
        assert variant.total_estimated_cost_usd == Decimal("20")


def test_cost_total_is_null_when_incomplete(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session, persona_count=1, repeat_count=1
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    # No OPENAI_*_COST_PER_1M configured in the default test Settings, so
    # estimated_cost_usd is null on every persisted run.
    for variant in analytics.variant_metrics:
        assert variant.total_estimated_cost_usd is None


def test_persona_disagreement_and_diverges_flag(db_session: Session) -> None:
    project, experiment, personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=1,
        responses=[
            make_simulation_call_result(
                clarity_score=5, perceived_value_score=5, adoption_intent_score=5
            ),
            make_simulation_call_result(
                clarity_score=2, perceived_value_score=2, adoption_intent_score=2
            ),
            make_simulation_call_result(
                clarity_score=2, perceived_value_score=2, adoption_intent_score=2
            ),
            make_simulation_call_result(
                clarity_score=5, perceived_value_score=5, adoption_intent_score=5
            ),
        ],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    persona_ids = sorted(p.id for p in personas)
    assert [entry.persona_id for entry in analytics.persona_disagreement] == persona_ids

    first, second = analytics.persona_disagreement
    assert first.direction == "prefers_a"
    assert second.direction == "prefers_b"
    # Overall variant-level average is tied (3.5 vs 3.5) -> "neutral", so
    # both individually-directional personas diverge from it.
    assert first.diverges_from_overall_variant_direction is True
    assert second.diverges_from_overall_variant_direction is True


def test_persona_agreeing_with_overall_direction_does_not_diverge(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert all(
        entry.diverges_from_overall_variant_direction is False
        for entry in analytics.persona_disagreement
    )


def test_zero_completed_runs_rejected(db_session: Session) -> None:
    project, evidence, personas = _seed_draft(db_session)
    experiment = ExperimentService(db_session).create(
        project.id,
        ExperimentCreate(**experiment_create_payload([p.id for p in personas])),
    )
    # Force a completed-status experiment with no persisted runs at all,
    # to exercise the defensive "zero completed runs" guard directly.
    experiment.status = ExperimentStatus.COMPLETED
    db_session.commit()

    with pytest.raises(ConflictError):
        ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)


@pytest.mark.parametrize(
    "status", [ExperimentStatus.DRAFT, ExperimentStatus.RUNNING, ExperimentStatus.FAILED]
)
def test_ineligible_statuses_are_rejected(db_session: Session, status: ExperimentStatus) -> None:
    project, evidence, personas = _seed_draft(db_session)
    experiment = ExperimentService(db_session).create(
        project.id,
        ExperimentCreate(**experiment_create_payload([p.id for p in personas])),
    )
    experiment.status = status
    db_session.commit()

    with pytest.raises(ConflictError):
        ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)


def test_one_variant_zero_completed_runs_produces_warning_and_flag(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        responses=[make_simulation_call_result(), LLMTimeoutError("timed out")],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.data_quality_flags.variant_b_zero_completed_runs is True
    assert analytics.data_quality_flags.variant_a_zero_completed_runs is False
    assert any("Variant B" in warning for warning in analytics.data_quality_warnings)
    assert analytics.coverage.data_quality_warnings == analytics.data_quality_warnings


def test_fewer_than_two_personas_produces_warning_and_flag(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=1,
        responses=[
            make_simulation_call_result(),
            LLMTimeoutError("timed out"),
            make_simulation_call_result(),
            LLMTimeoutError("timed out"),
        ],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.data_quality_flags.insufficient_persona_coverage is True
    assert analytics.data_quality_flags.variant_a_zero_completed_runs is False
    assert analytics.data_quality_flags.variant_b_zero_completed_runs is False
    assert any("Fewer than two personas" in warning for warning in analytics.data_quality_warnings)


def test_severe_failure_imbalance_flag_in_isolation(db_session: Session) -> None:
    ok = make_simulation_call_result()
    err = LLMTimeoutError("timed out")
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=3,
        responses=[ok, err, err, ok, err, err, ok, err, err, ok, err, err],
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.data_quality_flags.severe_failure_imbalance is True
    assert analytics.data_quality_flags.variant_a_zero_completed_runs is False
    assert analytics.data_quality_flags.variant_b_zero_completed_runs is False
    assert analytics.data_quality_flags.insufficient_persona_coverage is False


def test_no_evidence_citations_flag(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session,
        persona_count=1,
        repeat_count=1,
        result=make_simulation_call_result(evidence_item_id=None),
    )
    analytics = ExperimentAnalyticsService(db_session).analyze(project.id, experiment.id)

    assert analytics.data_quality_flags.no_evidence_citations is True
    assert analytics.evidence_coverage.completed_runs_with_evidence == 0
    assert analytics.evidence_coverage.evidence_citation_rate == 0.0


def _seed_draft(db_session: Session):
    return seed_project_with_personas(db_session, persona_count=1)
