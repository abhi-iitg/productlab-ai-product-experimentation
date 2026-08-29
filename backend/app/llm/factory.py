"""Centralized LLM provider selection.

The single place that decides whether a request-scoped LLM call uses the
real OpenAI-backed provider or a deterministic E2E fake. Every route's
`get_*_provider` FastAPI dependency delegates here instead of branching
itself, so provider selection stays centralized and route functions never
contain fake/real logic of their own.

`Settings` already refuses to start if `E2E_FAKE_AI=true` outside
`APP_ENV=test` (see `app.core.config`); the check is repeated here so this
module is safe to call directly, not only via the FastAPI dependency graph.
"""

from app.core.config import Settings, get_settings
from app.llm.decision_provider import DecisionMemoLLMProvider
from app.llm.e2e_fake_providers import (
    E2EFakeDecisionMemoProvider,
    E2EFakeInsightProvider,
    E2EFakePersonaProvider,
    E2EFakeSimulationProvider,
)
from app.llm.insight_provider import InsightLLMProvider
from app.llm.openai_decision_provider import OpenAIDecisionMemoProvider
from app.llm.openai_insight_provider import OpenAIInsightProvider
from app.llm.openai_provider import OpenAIPersonaProvider
from app.llm.openai_simulation_provider import OpenAISimulationProvider
from app.llm.provider import PersonaLLMProvider
from app.llm.simulation_provider import SimulationLLMProvider


def _fake_ai_enabled(settings: Settings) -> bool:
    if not settings.E2E_FAKE_AI:
        return False
    if settings.APP_ENV != "test":
        raise RuntimeError(
            "E2E_FAKE_AI=true is only permitted when APP_ENV=test. Refusing to "
            "select fake AI providers outside the test environment."
        )
    return True


def build_persona_provider(settings: Settings | None = None) -> PersonaLLMProvider:
    settings = settings or get_settings()
    if _fake_ai_enabled(settings):
        return E2EFakePersonaProvider()
    return OpenAIPersonaProvider(settings=settings)


def build_simulation_provider(settings: Settings | None = None) -> SimulationLLMProvider:
    settings = settings or get_settings()
    if _fake_ai_enabled(settings):
        return E2EFakeSimulationProvider()
    return OpenAISimulationProvider(settings=settings)


def build_insight_provider(settings: Settings | None = None) -> InsightLLMProvider:
    settings = settings or get_settings()
    if _fake_ai_enabled(settings):
        return E2EFakeInsightProvider()
    return OpenAIInsightProvider(settings=settings)


def build_decision_memo_provider(settings: Settings | None = None) -> DecisionMemoLLMProvider:
    settings = settings or get_settings()
    if _fake_ai_enabled(settings):
        return E2EFakeDecisionMemoProvider()
    return OpenAIDecisionMemoProvider(settings=settings)
