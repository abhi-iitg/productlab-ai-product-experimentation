"""OpenAIPersonaProvider: lazy client init and safe failure handling.

No test here makes a network call. `generate_personas` is only exercised
in configurations that fail before any HTTP request would be sent (missing
API key); actual request/response handling is covered by `FakePersonaProvider`
elsewhere, since the real provider is a thin, typed wrapper around the
OpenAI SDK.
"""

import pytest

from app.core.config import Settings
from app.llm.exceptions import LLMConfigurationError
from app.llm.openai_provider import OpenAIPersonaProvider


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_constructing_provider_does_not_require_api_key() -> None:
    # Must not raise: constructing the provider (and importing this module)
    # never touches OPENAI_API_KEY.
    provider = OpenAIPersonaProvider(_settings(OPENAI_API_KEY=None))
    assert provider.model_name == "gpt-4o-mini"


def test_model_name_reflects_configured_model() -> None:
    provider = OpenAIPersonaProvider(_settings(OPENAI_MODEL="gpt-4.1-mini"))
    assert provider.model_name == "gpt-4.1-mini"


def test_generate_personas_raises_configuration_error_without_api_key() -> None:
    provider = OpenAIPersonaProvider(_settings(OPENAI_API_KEY=None))

    with pytest.raises(LLMConfigurationError):
        provider.generate_personas(
            persona_count=2, context="context", focus=None, allowed_evidence_ids={1}
        )


def test_generate_personas_raises_configuration_error_for_placeholder_api_key() -> None:
    provider = OpenAIPersonaProvider(_settings(OPENAI_API_KEY="changeme"))

    with pytest.raises(LLMConfigurationError):
        provider.generate_personas(
            persona_count=2, context="context", focus=None, allowed_evidence_ids={1}
        )
