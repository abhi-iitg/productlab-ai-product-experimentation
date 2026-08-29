"""Centralized LLM provider selection (Stage 9A E2E fake-provider gating).

`app.llm.factory` is the only place that decides real vs. fake provider
selection; route `get_*_provider` dependencies just delegate to it (see
`app/api/routes/personas.py`, `experiments.py`, `analysis.py`).
"""

import pytest

from app.core.config import Settings
from app.llm.e2e_fake_providers import (
    E2EFakeDecisionMemoProvider,
    E2EFakeInsightProvider,
    E2EFakePersonaProvider,
    E2EFakeSimulationProvider,
)
from app.llm.factory import (
    build_decision_memo_provider,
    build_insight_provider,
    build_persona_provider,
    build_simulation_provider,
)
from app.llm.openai_decision_provider import OpenAIDecisionMemoProvider
from app.llm.openai_insight_provider import OpenAIInsightProvider
from app.llm.openai_provider import OpenAIPersonaProvider
from app.llm.openai_simulation_provider import OpenAISimulationProvider

_CASES = [
    (build_persona_provider, E2EFakePersonaProvider, OpenAIPersonaProvider),
    (build_simulation_provider, E2EFakeSimulationProvider, OpenAISimulationProvider),
    (build_insight_provider, E2EFakeInsightProvider, OpenAIInsightProvider),
    (build_decision_memo_provider, E2EFakeDecisionMemoProvider, OpenAIDecisionMemoProvider),
]


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


@pytest.mark.parametrize(("build", "fake_type", "real_type"), _CASES)
def test_factory_selects_real_provider_by_default(build, fake_type, real_type) -> None:
    provider = build(_settings())

    assert isinstance(provider, real_type)
    assert not isinstance(provider, fake_type)


@pytest.mark.parametrize(("build", "fake_type", "real_type"), _CASES)
def test_factory_selects_fake_provider_in_e2e_test_mode(build, fake_type, real_type) -> None:
    provider = build(_settings(APP_ENV="test", E2E_FAKE_AI=True))

    assert isinstance(provider, fake_type)
    assert not isinstance(provider, real_type)


@pytest.mark.parametrize(("build", "fake_type", "real_type"), _CASES)
def test_factory_uses_real_provider_when_test_env_but_flag_unset(
    build, fake_type, real_type
) -> None:
    provider = build(_settings(APP_ENV="test"))

    assert isinstance(provider, real_type)


@pytest.mark.parametrize(("build", "_fake_type", "_real_type"), _CASES)
def test_factory_refuses_fake_provider_outside_test_env(build, _fake_type, _real_type) -> None:
    """Defense-in-depth: even if a caller mutates settings after construction
    (bypassing `Settings`' own startup validator), the factory itself still
    refuses to select a fake provider outside `APP_ENV=test`.
    """
    settings = _settings(APP_ENV="test", E2E_FAKE_AI=True)
    settings.APP_ENV = "production"

    with pytest.raises(RuntimeError):
        build(settings)
