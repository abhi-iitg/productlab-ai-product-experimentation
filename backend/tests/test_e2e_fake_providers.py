"""Deterministic E2E fake providers (`app/llm/e2e_fake_providers.py`).

These are the providers Playwright exercises against the real running app
in E2E test mode. Unlike `tests/fakes.py`, they build a schema-valid
response directly from whatever IDs the caller passes in, so they need
their own coverage of that derivation logic.
"""

import pytest

from app.llm.e2e_fake_providers import (
    E2EFakeDecisionMemoProvider,
    E2EFakeInsightProvider,
    E2EFakePersonaProvider,
    E2EFakeSimulationProvider,
)
from app.llm.exceptions import LLMProviderError


def test_persona_provider_generates_requested_count_grounded_in_allowed_evidence() -> None:
    provider = E2EFakePersonaProvider()

    result = provider.generate_personas(
        persona_count=3, context="ctx", focus=None, allowed_evidence_ids={5, 7}
    )

    assert len(result.personas) == 3
    for persona in result.personas:
        assert persona.evidence_references
        for reference in persona.evidence_references:
            assert reference.evidence_item_id in {5, 7}


def test_persona_provider_first_persona_has_unsupported_assumption() -> None:
    provider = E2EFakePersonaProvider()

    result = provider.generate_personas(
        persona_count=2, context="ctx", focus=None, allowed_evidence_ids={1}
    )

    assert result.personas[0].unsupported_assumptions


def test_persona_provider_raises_without_evidence() -> None:
    provider = E2EFakePersonaProvider()

    with pytest.raises(LLMProviderError):
        provider.generate_personas(
            persona_count=2, context="ctx", focus=None, allowed_evidence_ids=set()
        )


def test_simulation_provider_is_deterministic_and_configured() -> None:
    provider = E2EFakeSimulationProvider()
    provider.ensure_configured()

    first = provider.run_simulation(context="ctx", allowed_evidence_ids={9})
    second = provider.run_simulation(context="ctx", allowed_evidence_ids={9})

    assert first.output.task_outcome == second.output.task_outcome
    assert first.output.evidence_references[0].evidence_item_id == 9


def test_simulation_provider_handles_no_evidence() -> None:
    provider = E2EFakeSimulationProvider()

    result = provider.run_simulation(context="ctx", allowed_evidence_ids=set())

    assert result.output.evidence_references == []


def test_insight_provider_references_only_allowed_runs_and_evidence() -> None:
    provider = E2EFakeInsightProvider()

    result = provider.generate_insights(
        context="ctx",
        allowed_run_ids={1, 2},
        run_evidence_ids={1: {10}, 2: {11}},
        run_persona_ids={1: 100, 2: 200},
    )

    assert len(result.insights) == 2
    for insight in result.insights:
        assert set(insight.supporting_run_ids) <= {1, 2}
        assert set(insight.supporting_evidence_ids) <= {10, 11}
        assert insight.frequency == len(insight.supporting_run_ids)
        assert insight.persona_count == 2


def test_insight_provider_raises_without_runs() -> None:
    provider = E2EFakeInsightProvider()

    with pytest.raises(LLMProviderError):
        provider.generate_insights(
            context="ctx", allowed_run_ids=set(), run_evidence_ids={}, run_persona_ids={}
        )


def test_decision_memo_provider_proceeds_with_safe_language() -> None:
    provider = E2EFakeDecisionMemoProvider()

    candidate = provider.generate_decision_memo(context="ctx", allowed_insight_ids={1, 2})

    assert candidate.supporting_insight_ids == [1, 2]
    assert "real-user validation" in candidate.executive_summary.casefold()
    assert candidate.uncertain_conclusions
    assert "evidence" in " ".join(candidate.uncertain_conclusions).casefold()


def test_decision_memo_provider_raises_without_insights() -> None:
    provider = E2EFakeDecisionMemoProvider()

    with pytest.raises(LLMProviderError):
        provider.generate_decision_memo(context="ctx", allowed_insight_ids=set())
