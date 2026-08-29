"""Typed failures raised by LLM provider implementations.

`PersonaGenerationService` catches these and translates them into the safe,
generic `app.core.exceptions` errors the API boundary returns — provider
internals (status codes, SDK exception text, request IDs) never reach the
client.
"""


class LLMProviderError(Exception):
    """Base class for all provider-abstraction failures."""


class LLMConfigurationError(LLMProviderError):
    """The provider is missing required configuration (e.g. no API key)."""


class LLMTimeoutError(LLMProviderError):
    """The provider request timed out."""


class LLMRateLimitError(LLMProviderError):
    """The provider rejected the request due to rate limiting."""


class LLMStatusError(LLMProviderError):
    """The provider returned an error status."""


class LLMEmptyOutputError(LLMProviderError):
    """The provider returned no usable output text."""


class LLMInvalidOutputError(LLMProviderError):
    """The provider output was not valid JSON, or failed schema validation."""


class LLMMalformedJSONError(LLMInvalidOutputError):
    """The provider output was not valid JSON.

    Used by the simulation provider, which (unlike the persona provider)
    must distinguish this from schema-validation failures so
    `SimulationRun.failure_type` records the precise safe category.
    """


class LLMInvalidSchemaError(LLMInvalidOutputError):
    """The provider output was valid JSON but failed schema validation."""


class LLMInvalidEvidenceReferenceError(LLMInvalidSchemaError):
    """The provider output cited an evidence ID not available to the persona."""
