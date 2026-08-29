"""OpenAISimulationProvider: lazy client init and safe failure handling.

No test here makes a network call. `run_simulation` is only exercised in
configurations that fail before any HTTP request would be sent (missing API
key); actual request/response handling is covered by `FakeSimulationProvider`
elsewhere, since the real provider is a thin, typed wrapper around the
OpenAI SDK.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings
from app.llm.exceptions import LLMConfigurationError
from app.llm.openai_simulation_provider import (
    OpenAISimulationProvider,
    _is_evidence_reference_error,
)
from app.schemas.simulation_run import SimulationOutput


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_constructing_provider_does_not_require_api_key() -> None:
    provider = OpenAISimulationProvider(_settings(OPENAI_API_KEY=None))
    assert provider.model_name == "gpt-4o-mini"


def test_model_name_reflects_configured_model() -> None:
    provider = OpenAISimulationProvider(_settings(OPENAI_MODEL="gpt-4.1-mini"))
    assert provider.model_name == "gpt-4.1-mini"


def test_ensure_configured_raises_without_api_key() -> None:
    provider = OpenAISimulationProvider(_settings(OPENAI_API_KEY=None))
    with pytest.raises(LLMConfigurationError):
        provider.ensure_configured()


def test_ensure_configured_raises_for_placeholder_api_key() -> None:
    provider = OpenAISimulationProvider(_settings(OPENAI_API_KEY="changeme"))
    with pytest.raises(LLMConfigurationError):
        provider.ensure_configured()


def test_ensure_configured_succeeds_with_real_looking_key() -> None:
    provider = OpenAISimulationProvider(_settings(OPENAI_API_KEY="sk-test-key"))
    provider.ensure_configured()  # must not raise


def test_run_simulation_raises_configuration_error_without_api_key() -> None:
    provider = OpenAISimulationProvider(_settings(OPENAI_API_KEY=None))
    with pytest.raises(LLMConfigurationError):
        provider.run_simulation(context="context", allowed_evidence_ids={1})


def _valid_output_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "task_outcome": "completed",
        "clarity_score": 4,
        "perceived_value_score": 4,
        "adoption_intent_score": 4,
        "response_summary": "Clear reaction.",
        "positive_signals": [],
        "objections": [],
        "confusion_points": [],
        "feature_requests": [],
        "uncertainty_notes": [],
        "evidence_references": [{"evidence_item_id": 99, "supported_claims": ["Invented."]}],
    }
    payload.update(overrides)
    return payload


def test_is_evidence_reference_error_true_for_evidence_only_errors() -> None:
    try:
        SimulationOutput.model_validate(
            _valid_output_payload(), context={"allowed_evidence_ids": {1}}
        )
    except PydanticValidationError as exc:
        assert _is_evidence_reference_error(exc) is True
    else:
        pytest.fail("expected a validation error")


def test_is_evidence_reference_error_false_for_other_schema_errors() -> None:
    payload = _valid_output_payload(clarity_score=99, evidence_references=[])
    try:
        SimulationOutput.model_validate(payload, context={"allowed_evidence_ids": {1}})
    except PydanticValidationError as exc:
        assert _is_evidence_reference_error(exc) is False
    else:
        pytest.fail("expected a validation error")
