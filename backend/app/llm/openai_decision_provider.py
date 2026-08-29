"""OpenAI Responses API implementation of `DecisionMemoLLMProvider` (Stage 6).

Reads configuration from `app.core.config.Settings`. The client is
constructed lazily on first use, not in `__init__`, so importing this
module or constructing the provider never requires `OPENAI_API_KEY` — only
an actual generation call does. No streaming is used.

Even though the request asks the provider for structured JSON output, that
alone is not trusted: the raw output text is parsed with `json.loads` and
validated against `DecisionMemoCandidate` locally, exactly as the persona,
simulation, and Insight providers do.
"""

import json
import logging

from openai import APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings, get_settings
from app.llm.decision_prompts import build_decision_system_instructions, build_decision_user_prompt
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidSchemaError,
    LLMMalformedJSONError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.schemas.decision_memo import DecisionMemoCandidate

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SECONDS = 30.0
_PLACEHOLDER_API_KEYS = {"", "changeme"}


class OpenAIDecisionMemoProvider:
    """Decision Memo generation via the OpenAI Responses API."""

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

    def generate_decision_memo(
        self,
        *,
        context: str,
        allowed_insight_ids: set[int],
    ) -> DecisionMemoCandidate:
        client = self._get_client()
        system_instructions = build_decision_system_instructions()
        user_prompt = build_decision_user_prompt(context)

        logger.info(
            "Requesting decision memo generation (model=%s, insight_count=%d)",
            self.model_name,
            len(allowed_insight_ids),
        )

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

        output_text = getattr(response, "output_text", None)
        if not output_text or not output_text.strip():
            raise LLMEmptyOutputError("The AI provider returned an empty response.")

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise LLMMalformedJSONError("The AI provider returned malformed JSON.") from exc

        try:
            return DecisionMemoCandidate.model_validate(
                parsed, context={"allowed_insight_ids": allowed_insight_ids}
            )
        except PydanticValidationError as exc:
            raise LLMInvalidSchemaError(
                "The AI provider response did not match the required schema."
            ) from exc
