"""Pydantic validation for the untrusted SimulationOutput LLM-output schema."""

import pytest
from pydantic import ValidationError

from app.models.simulation_run import TaskOutcome
from app.schemas.simulation_run import SimulationCallResult, SimulationOutput


def _valid_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "task_outcome": "completed",
        "clarity_score": 4,
        "perceived_value_score": 5,
        "adoption_intent_score": 3,
        "response_summary": "The persona found the flow clear and would try it.",
        "positive_signals": ["Liked the shorter flow.", " liked the shorter flow. "],
        "objections": [],
        "confusion_points": [],
        "feature_requests": [],
        "uncertainty_notes": [],
        "evidence_references": [{"evidence_item_id": 1, "supported_claims": ["Matches evidence."]}],
    }
    payload.update(overrides)
    return payload


def test_valid_simulation_output() -> None:
    output = SimulationOutput.model_validate(
        _valid_payload(), context={"allowed_evidence_ids": {1}}
    )
    assert output.task_outcome == TaskOutcome.COMPLETED
    # Deduplicated case-insensitively after trimming.
    assert output.positive_signals == ["Liked the shorter flow."]


@pytest.mark.parametrize(
    "field", ["clarity_score", "perceived_value_score", "adoption_intent_score"]
)
@pytest.mark.parametrize("value", [0, 6])
def test_scores_are_constrained_between_one_and_five(field: str, value: int) -> None:
    payload = _valid_payload(**{field: value})
    with pytest.raises(ValidationError):
        SimulationOutput.model_validate(payload, context={"allowed_evidence_ids": {1}})


def test_response_summary_cannot_be_blank() -> None:
    payload = _valid_payload(response_summary="   ")
    with pytest.raises(ValidationError):
        SimulationOutput.model_validate(payload, context={"allowed_evidence_ids": {1}})


def test_evidence_reference_must_be_within_allowed_ids() -> None:
    payload = _valid_payload(
        evidence_references=[{"evidence_item_id": 99, "supported_claims": ["Invented."]}]
    )
    with pytest.raises(ValidationError):
        SimulationOutput.model_validate(payload, context={"allowed_evidence_ids": {1}})


def test_evidence_references_may_be_empty() -> None:
    payload = _valid_payload(evidence_references=[])
    output = SimulationOutput.model_validate(payload, context={"allowed_evidence_ids": {1}})
    assert output.evidence_references == []


def test_invalid_task_outcome_rejected() -> None:
    payload = _valid_payload(task_outcome="not_a_real_outcome")
    with pytest.raises(ValidationError):
        SimulationOutput.model_validate(payload, context={"allowed_evidence_ids": {1}})


def test_simulation_call_result_rejects_negative_tokens() -> None:
    output = SimulationOutput.model_validate(
        _valid_payload(), context={"allowed_evidence_ids": {1}}
    )
    with pytest.raises(ValidationError):
        SimulationCallResult(output=output, input_tokens=-1, output_tokens=10, latency_ms=5)


def test_simulation_call_result_rejects_negative_latency() -> None:
    output = SimulationOutput.model_validate(
        _valid_payload(), context={"allowed_evidence_ids": {1}}
    )
    with pytest.raises(ValidationError):
        SimulationCallResult(output=output, input_tokens=10, output_tokens=10, latency_ms=-1)


def test_simulation_call_result_allows_null_token_counts() -> None:
    output = SimulationOutput.model_validate(
        _valid_payload(), context={"allowed_evidence_ids": {1}}
    )
    result = SimulationCallResult(
        output=output, input_tokens=None, output_tokens=None, latency_ms=10
    )
    assert result.input_tokens is None
    assert result.output_tokens is None
