"""OpenAI Responses API implementation of `SimulationLLMProvider`.

Reads configuration from `app.core.config.Settings`. The client is
constructed lazily on first use (via `_get_client`), not in `__init__`, so
importing this module or constructing the provider never requires
`OPENAI_API_KEY` — only `ensure_configured()` or an actual simulation call
does. No streaming is used.

Even though the request asks the provider for structured JSON output, that
alone is not trusted: the raw output text is parsed with `json.loads` and
validated against `SimulationOutput` locally, exactly as if the provider had
returned unstructured text.
"""

import json
import logging
import time

from openai import APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings, get_settings
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidEvidenceReferenceError,
    LLMInvalidSchemaError,
    LLMMalformedJSONError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.llm.simulation_prompts import (
    build_simulation_system_instructions,
    build_simulation_user_prompt,
)
from app.schemas.simulation_run import SimulationCallResult, SimulationOutput

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 30.0
_PLACEHOLDER_API_KEYS = {"", "changeme"}


def _is_evidence_reference_error(exc: PydanticValidationError) -> bool:
    """True if every validation error originates from the evidence-reference check.

    Lets the provider raise the more specific `LLMInvalidEvidenceReferenceError`
    instead of the generic `LLMInvalidSchemaError` when that's the only thing
    wrong with an otherwise schema-valid response.
    """
    errors = exc.errors()
    if not errors:
        return False
    return all("evidence_references" in error["loc"] for error in errors)


class OpenAISimulationProvider:
    """Structured simulation-run execution via the OpenAI Responses API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: OpenAI | None = None

    @property
    def model_name(self) -> str:
        return self._settings.OPENAI_MODEL

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = self._settings.OPENAI_API_KEY
            if not api_key or api_key in _PLACEHOLDER_API_KEYS:
                raise LLMConfigurationError("OPENAI_API_KEY is not configured.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def ensure_configured(self) -> None:
        self._get_client()

    def run_simulation(
        self,
        *,
        context: str,
        allowed_evidence_ids: set[int],
    ) -> SimulationCallResult:
        client = self._get_client()
        system_instructions = build_simulation_system_instructions()
        user_prompt = build_simulation_user_prompt(context)

        logger.info(
            "Requesting simulation run (model=%s, evidence_count=%d)",
            self.model_name,
            len(allowed_evidence_ids),
        )

        start = time.monotonic()
        try:
            response = client.responses.create(
                model=self.model_name,
                instructions=system_instructions,
                input=user_prompt,
                text={"format": {"type": "json_object"}},
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
        except APITimeoutError as exc:
            raise LLMTimeoutError("The AI provider request timed out.") from exc
        except RateLimitError as exc:
            raise LLMRateLimitError("The AI provider rate limit was exceeded.") from exc
        except APIStatusError as exc:
            raise LLMStatusError("The AI provider returned an error status.") from exc
        latency_ms = round((time.monotonic() - start) * 1000)

        output_text = getattr(response, "output_text", None)
        if not output_text or not output_text.strip():
            raise LLMEmptyOutputError("The AI provider returned an empty response.")

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise LLMMalformedJSONError("The AI provider returned malformed JSON.") from exc

        try:
            output = SimulationOutput.model_validate(
                parsed, context={"allowed_evidence_ids": allowed_evidence_ids}
            )
        except PydanticValidationError as exc:
            if _is_evidence_reference_error(exc):
                raise LLMInvalidEvidenceReferenceError(
                    "The AI provider response cited evidence not available to this persona."
                ) from exc
            raise LLMInvalidSchemaError(
                "The AI provider response did not match the required schema."
            ) from exc

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None

        return SimulationCallResult(
            output=output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
