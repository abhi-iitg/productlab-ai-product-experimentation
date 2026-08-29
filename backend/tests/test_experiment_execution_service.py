"""ExperimentExecutionService: run-matrix execution, per-run failure handling,
final status derivation, and transaction/commit strategy.

Every provider interaction is driven through `FakeSimulationProvider` — no
test here ever calls OpenAI or the network.
"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ConflictError, InvalidRequestError, ProviderConfigurationError
from app.llm.exceptions import (
    LLMEmptyOutputError,
    LLMInvalidEvidenceReferenceError,
    LLMInvalidSchemaError,
    LLMMalformedJSONError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.models.experiment import ExperimentStatus
from app.models.simulation_run import FailureType, SimulationRunStatus
from app.models.variant import VariantKey
from app.schemas.experiment import ExperimentCreate, ExperimentExecuteRequest
from app.services.experiment import ExperimentService
from app.services.experiment_execution import ExperimentExecutionService
from tests.experiment_helpers import experiment_create_payload, seed_project_with_personas
from tests.fakes import FakeSimulationProvider, make_simulation_call_result

_CONFIRM = ExperimentExecuteRequest(confirm_execution=True)


def _draft_experiment(db_session: Session, *, persona_count: int = 1, **overrides: object):
    project, evidence, personas = seed_project_with_personas(
        db_session, persona_count=persona_count
    )
    experiment = ExperimentService(db_session).create(
        project.id,
        ExperimentCreate(**experiment_create_payload([p.id for p in personas], **overrides)),
    )
    return project, evidence, personas, experiment


def test_successful_full_execution(db_session: Session) -> None:
    project, _evidence, personas, experiment = _draft_experiment(db_session, repeat_count=2)
    provider = FakeSimulationProvider(result=make_simulation_call_result())
    service = ExperimentExecutionService(db_session, provider)

    summary = service.execute(project.id, experiment.id, _CONFIRM)

    assert summary.status == ExperimentStatus.COMPLETED
    assert summary.total_runs == 4  # 1 persona x 2 variants x 2 repeats
    assert summary.completed_runs == 4
    assert summary.failed_runs == 0
    assert summary.started_at is not None
    assert summary.completed_at is not None

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert len(runs) == 4
    assert all(run.status == SimulationRunStatus.COMPLETED for run in runs)


def test_stable_run_matrix_ordering(db_session: Session) -> None:
    project, _evidence, personas, experiment = _draft_experiment(
        db_session, persona_count=2, repeat_count=2
    )
    provider = FakeSimulationProvider(result=make_simulation_call_result())
    service = ExperimentExecutionService(db_session, provider)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    variant_by_id = {v.id: v.key for v in experiment.variants}
    ordered_persona_ids = sorted(p.id for p in personas)

    expected = []
    for variant_key in (VariantKey.A, VariantKey.B):
        for persona_id in ordered_persona_ids:
            for repetition_index in (0, 1):
                expected.append((variant_key, persona_id, repetition_index))

    actual = [(variant_by_id[run.variant_id], run.persona_id, run.repetition_index) for run in runs]
    assert actual == expected


def test_repeat_execution_is_rejected(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session)
    provider = FakeSimulationProvider(result=make_simulation_call_result())
    service = ExperimentExecutionService(db_session, provider)
    service.execute(project.id, experiment.id, _CONFIRM)

    with pytest.raises(ConflictError):
        service.execute(project.id, experiment.id, _CONFIRM)


def test_mixed_success_and_failure_produces_partially_completed(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    # 1 persona x 2 variants x 1 repeat = 2 runs: first succeeds, second fails.
    provider = FakeSimulationProvider(
        responses=[make_simulation_call_result(), LLMTimeoutError("timed out")]
    )
    service = ExperimentExecutionService(db_session, provider)

    summary = service.execute(project.id, experiment.id, _CONFIRM)

    assert summary.status == ExperimentStatus.PARTIALLY_COMPLETED
    assert summary.completed_runs == 1
    assert summary.failed_runs == 1


def test_all_failures_produce_failed_status(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(error=LLMTimeoutError("timed out"))
    service = ExperimentExecutionService(db_session, provider)

    summary = service.execute(project.id, experiment.id, _CONFIRM)

    assert summary.status == ExperimentStatus.FAILED
    assert summary.completed_runs == 0
    assert summary.failed_runs == 2


_SENSITIVE_DETAIL = "internal-detail sk-secret-abc123 request_id=req_9f8e request to api.openai.com"


@pytest.mark.parametrize(
    ("error", "expected_failure_type"),
    [
        (LLMTimeoutError(_SENSITIVE_DETAIL), FailureType.TIMEOUT),
        (LLMRateLimitError(_SENSITIVE_DETAIL), FailureType.RATE_LIMIT),
        (LLMStatusError(_SENSITIVE_DETAIL), FailureType.PROVIDER_ERROR),
        (LLMEmptyOutputError(_SENSITIVE_DETAIL), FailureType.EMPTY_OUTPUT),
        (LLMMalformedJSONError(_SENSITIVE_DETAIL), FailureType.MALFORMED_JSON),
        (LLMInvalidSchemaError(_SENSITIVE_DETAIL), FailureType.INVALID_SCHEMA),
        (
            LLMInvalidEvidenceReferenceError(_SENSITIVE_DETAIL),
            FailureType.INVALID_EVIDENCE_REFERENCE,
        ),
    ],
)
def test_provider_failure_categories_recorded_safely(
    db_session: Session, error: Exception, expected_failure_type: FailureType
) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(error=error)
    service = ExperimentExecutionService(db_session, provider)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert all(run.status == SimulationRunStatus.FAILED for run in runs)
    assert all(run.failure_type == expected_failure_type for run in runs)
    for run in runs:
        assert run.failure_message
        assert "Traceback" not in run.failure_message
        assert _SENSITIVE_DETAIL not in run.failure_message


def test_unexpected_error_is_recorded_as_unexpected_error(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(error=RuntimeError("something broke internally"))
    service = ExperimentExecutionService(db_session, provider)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert all(run.failure_type == FailureType.UNEXPECTED_ERROR for run in runs)
    assert all("something broke internally" not in (run.failure_message or "") for run in runs)


def test_context_limit_fails_safely_without_contacting_provider(db_session: Session) -> None:
    project, _evidence, personas, experiment = _draft_experiment(db_session, repeat_count=1)
    # Blow up the evidence content this persona cites so the assembled
    # context exceeds SIMULATION_CONTEXT_CHAR_LIMIT before any call is made.
    from app.models.evidence_item import EvidenceItem

    evidence = db_session.get(EvidenceItem, personas[0].evidence_references[0]["evidence_item_id"])
    evidence.content = "x" * 25_000
    db_session.commit()

    provider = FakeSimulationProvider(result=make_simulation_call_result())
    service = ExperimentExecutionService(db_session, provider)

    summary = service.execute(project.id, experiment.id, _CONFIRM)

    assert summary.status == ExperimentStatus.FAILED
    assert provider.calls == []  # provider was never contacted
    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert all(run.failure_type == FailureType.CONTEXT_LIMIT for run in runs)


def test_individual_failure_does_not_erase_earlier_completed_runs(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(
        responses=[make_simulation_call_result(), LLMTimeoutError("timed out")]
    )
    service = ExperimentExecutionService(db_session, provider)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    statuses = [run.status for run in runs]
    assert SimulationRunStatus.COMPLETED in statuses
    assert SimulationRunStatus.FAILED in statuses


def test_no_duplicate_run_rows(db_session: Session) -> None:
    project, _evidence, personas, experiment = _draft_experiment(
        db_session, persona_count=2, repeat_count=2
    )
    provider = FakeSimulationProvider(result=make_simulation_call_result())
    service = ExperimentExecutionService(db_session, provider)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    keys = {
        (run.experiment_id, run.variant_id, run.persona_id, run.repetition_index) for run in runs
    }
    assert len(keys) == len(runs) == 8


def test_final_status_and_timestamps_persisted(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session)
    provider = FakeSimulationProvider(result=make_simulation_call_result())
    service = ExperimentExecutionService(db_session, provider)

    service.execute(project.id, experiment.id, _CONFIRM)

    refreshed = ExperimentService(db_session).get(project.id, experiment.id)
    assert refreshed.status == ExperimentStatus.COMPLETED
    assert refreshed.started_at is not None
    assert refreshed.completed_at is not None


def test_token_and_latency_metadata_persisted(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(
        result=make_simulation_call_result(input_tokens=111, output_tokens=222, latency_ms=333)
    )
    service = ExperimentExecutionService(db_session, provider)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert all(run.input_tokens == 111 for run in runs)
    assert all(run.output_tokens == 222 for run in runs)
    assert all(run.latency_ms == 333 for run in runs)


def test_cost_estimated_when_rates_configured(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(
        result=make_simulation_call_result(input_tokens=1_000_000, output_tokens=1_000_000)
    )
    settings = Settings(
        _env_file=None,
        OPENAI_INPUT_COST_PER_1M=Decimal("5"),
        OPENAI_OUTPUT_COST_PER_1M=Decimal("15"),
    )
    service = ExperimentExecutionService(db_session, provider, settings=settings)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert all(run.estimated_cost_usd == Decimal("20") for run in runs)


def test_cost_null_when_rates_absent(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(result=make_simulation_call_result())
    settings = Settings(_env_file=None)
    service = ExperimentExecutionService(db_session, provider, settings=settings)

    service.execute(project.id, experiment.id, _CONFIRM)

    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert all(run.estimated_cost_usd is None for run in runs)


def test_provider_configuration_failure_returns_service_error(db_session: Session) -> None:
    project, _evidence, _personas, experiment = _draft_experiment(db_session)
    provider = FakeSimulationProvider(configured=False)
    service = ExperimentExecutionService(db_session, provider)

    with pytest.raises(ProviderConfigurationError):
        service.execute(project.id, experiment.id, _CONFIRM)

    refreshed = ExperimentService(db_session).get(project.id, experiment.id)
    assert refreshed.status == ExperimentStatus.DRAFT
    assert ExperimentService(db_session).list_runs(project.id, experiment.id) == []


def test_run_level_configuration_error_recorded_safely(db_session: Session) -> None:
    from app.llm.exceptions import LLMConfigurationError

    project, _evidence, _personas, experiment = _draft_experiment(db_session, repeat_count=1)
    provider = FakeSimulationProvider(configured=True, error=LLMConfigurationError("no key"))
    service = ExperimentExecutionService(db_session, provider)

    summary = service.execute(project.id, experiment.id, _CONFIRM)

    assert summary.status == ExperimentStatus.FAILED
    runs = ExperimentService(db_session).list_runs(project.id, experiment.id)
    assert all(run.failure_type == FailureType.CONFIGURATION_ERROR for run in runs)


def test_over_run_limit_is_rejected_at_execution_time(db_session: Session) -> None:
    project, _evidence, personas, experiment = _draft_experiment(
        db_session, persona_count=6, repeat_count=2
    )
    # Force the calculated total above 30 by lowering repeat_count post-creation
    # is not possible on a draft via the same validation, so instead exercise
    # the execution-time guard directly by mutating repeat_count on the model.
    experiment.repeat_count = 3
    db_session.commit()

    provider = FakeSimulationProvider(result=make_simulation_call_result())
    service = ExperimentExecutionService(db_session, provider)

    with pytest.raises(InvalidRequestError):
        service.execute(project.id, experiment.id, _CONFIRM)
