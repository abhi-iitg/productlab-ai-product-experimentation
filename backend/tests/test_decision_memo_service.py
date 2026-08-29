"""DecisionMemoService: eligibility, atomic persistence, duplicate
prevention, decision safety rules, and safe translation of every
provider/validation failure mode.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ProviderConfigurationError,
    ProviderError,
)
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidSchemaError,
    LLMMalformedJSONError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.models.decision_memo import Recommendation
from app.repositories.decision_memo import DecisionMemoRepository
from app.services.decision_memo import DecisionMemoService
from app.services.insight_generation import InsightGenerationService
from tests.experiment_helpers import seed_completed_experiment
from tests.fakes import (
    FakeDecisionMemoProvider,
    FakeInsightProvider,
    make_decision_memo_candidate,
    make_insight_generation_result,
    make_real_user_test_plan,
    make_simulation_call_result,
)


def _seed_experiment_with_insights(db_session: Session, **experiment_overrides: object):
    project, experiment, personas, runs = seed_completed_experiment(
        db_session, **experiment_overrides
    )
    completed_ids = sorted(run.id for run in runs if run.status.value == "completed")
    persona_count = len({run.persona_id for run in runs if run.status.value == "completed"})
    insight_provider = FakeInsightProvider(
        result=make_insight_generation_result(
            supporting_run_ids=completed_ids, persona_count=persona_count
        )
    )
    insights = InsightGenerationService(db_session, insight_provider).generate(
        project.id, experiment.id
    )
    return project, experiment, insights


def test_successful_proceed_memo(db_session: Session) -> None:
    project, experiment, insights = _seed_experiment_with_insights(
        db_session, persona_count=2, repeat_count=1
    )
    candidate = make_decision_memo_candidate(
        recommendation=Recommendation.PROCEED,
        supporting_insight_ids=[i.id for i in insights],
    )
    memo = DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate)).generate(
        project.id, experiment.id
    )

    assert memo.recommendation == Recommendation.PROCEED
    assert memo.prompt_version == "decision-v1"
    assert DecisionMemoRepository(db_session).get_for_experiment(experiment.id).id == memo.id


def test_successful_iterate_memo(db_session: Session) -> None:
    project, experiment, insights = _seed_experiment_with_insights(
        db_session, persona_count=2, repeat_count=1
    )
    candidate = make_decision_memo_candidate(
        recommendation=Recommendation.ITERATE,
        executive_summary="Signal is mixed; address confusion before further testing.",
        supporting_insight_ids=[i.id for i in insights],
    )
    memo = DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate)).generate(
        project.id, experiment.id
    )

    assert memo.recommendation == Recommendation.ITERATE


def test_successful_stop_memo(db_session: Session) -> None:
    project, experiment, insights = _seed_experiment_with_insights(
        db_session, persona_count=2, repeat_count=1
    )
    candidate = make_decision_memo_candidate(
        recommendation=Recommendation.STOP,
        executive_summary="Signal is consistently weak; revisit the hypothesis.",
        supporting_insight_ids=[i.id for i in insights],
    )
    memo = DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate)).generate(
        project.id, experiment.id
    )

    assert memo.recommendation == Recommendation.STOP


def test_insights_required(db_session: Session) -> None:
    project, experiment, _personas, _runs = seed_completed_experiment(
        db_session, persona_count=2, repeat_count=1
    )
    provider = FakeDecisionMemoProvider()

    with pytest.raises(ConflictError):
        DecisionMemoService(db_session, provider).generate(project.id, experiment.id)


def test_duplicate_generation_rejected(db_session: Session) -> None:
    project, experiment, insights = _seed_experiment_with_insights(db_session)
    candidate = make_decision_memo_candidate(supporting_insight_ids=[i.id for i in insights])
    service = DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate))
    service.generate(project.id, experiment.id)

    with pytest.raises(ConflictError):
        service.generate(project.id, experiment.id)


def test_project_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        DecisionMemoService(db_session, FakeDecisionMemoProvider()).generate(999_999, 1)


def test_experiment_not_found(db_session: Session) -> None:
    project, _experiment, _insights = _seed_experiment_with_insights(db_session)
    with pytest.raises(NotFoundError):
        DecisionMemoService(db_session, FakeDecisionMemoProvider()).generate(project.id, 999_999)


def test_cross_experiment_isolation_returns_not_found(db_session: Session) -> None:
    _project_a, experiment_a, _insights_a = _seed_experiment_with_insights(db_session)
    project_b, _experiment_b, _insights_b = _seed_experiment_with_insights(db_session)

    with pytest.raises(NotFoundError):
        DecisionMemoService(db_session, FakeDecisionMemoProvider()).generate(
            project_b.id, experiment_a.id
        )


@pytest.mark.parametrize(
    "error",
    [
        LLMMalformedJSONError("bad json"),
        LLMEmptyOutputError("empty"),
        LLMInvalidSchemaError("bad schema"),
        LLMTimeoutError("timed out"),
        LLMRateLimitError("rate limited"),
        LLMStatusError("status error"),
    ],
)
def test_provider_failures_are_translated_and_nothing_persists(
    db_session: Session, error: Exception
) -> None:
    project, experiment, _insights = _seed_experiment_with_insights(db_session)
    provider = FakeDecisionMemoProvider(error=error)

    with pytest.raises(ProviderError):
        DecisionMemoService(db_session, provider).generate(project.id, experiment.id)

    assert DecisionMemoRepository(db_session).get_for_experiment(experiment.id) is None


def test_missing_configuration_returns_service_error(db_session: Session) -> None:
    project, experiment, _insights = _seed_experiment_with_insights(db_session)
    provider = FakeDecisionMemoProvider(error=LLMConfigurationError("no key"))

    with pytest.raises(ProviderConfigurationError):
        DecisionMemoService(db_session, provider).generate(project.id, experiment.id)


def test_proceed_rejected_with_severe_data_quality_warnings(db_session: Session) -> None:
    # One variant gets zero completed runs -> InsightGenerationService itself
    # already rejects this scenario, so exercise the memo-level safety rule
    # directly against a real experiment with a *different* severe condition:
    # fewer than two represented personas (achievable while both variants
    # still have completed runs, so Insight generation is allowed).
    project, experiment, personas, runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=1,
        responses=[
            make_simulation_call_result(),
            LLMTimeoutError("timed out"),
            make_simulation_call_result(),
            LLMTimeoutError("timed out"),
        ],
    )
    completed_ids = sorted(run.id for run in runs if run.status.value == "completed")
    insight_provider = FakeInsightProvider(
        result=make_insight_generation_result(supporting_run_ids=completed_ids, persona_count=1)
    )
    insights = InsightGenerationService(db_session, insight_provider).generate(
        project.id, experiment.id
    )
    candidate = make_decision_memo_candidate(
        recommendation=Recommendation.PROCEED, supporting_insight_ids=[i.id for i in insights]
    )

    with pytest.raises(ProviderError):
        DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate)).generate(
            project.id, experiment.id
        )
    assert DecisionMemoRepository(db_session).get_for_experiment(experiment.id) is None


def test_proceed_without_real_user_validation_phrase_rejected(db_session: Session) -> None:
    project, experiment, insights = _seed_experiment_with_insights(db_session)
    candidate = make_decision_memo_candidate(
        recommendation=Recommendation.PROCEED,
        executive_summary="We should launch immediately based on this signal.",
        supporting_insight_ids=[i.id for i in insights],
    )

    with pytest.raises(ProviderError):
        DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate)).generate(
            project.id, experiment.id
        )


@pytest.mark.parametrize(
    "phrase",
    [
        "this proves product-market fit",
        "ready to launch immediately",
        "guarantees market success",
        "predicts market success for this concept",
    ],
)
def test_market_validation_claims_rejected(db_session: Session, phrase: str) -> None:
    project, experiment, insights = _seed_experiment_with_insights(db_session)
    candidate = make_decision_memo_candidate(
        recommendation=Recommendation.ITERATE,
        executive_summary=f"Iterate: {phrase}.",
        supporting_insight_ids=[i.id for i in insights],
    )

    with pytest.raises(ProviderError):
        DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate)).generate(
            project.id, experiment.id
        )


def test_no_evidence_citations_requires_uncertainty_and_evidence_recommendation(
    db_session: Session,
) -> None:
    project, experiment, personas, runs = seed_completed_experiment(
        db_session,
        persona_count=2,
        repeat_count=1,
        result=make_simulation_call_result(evidence_item_id=None),
    )
    completed_ids = sorted(run.id for run in runs if run.status.value == "completed")
    insight_provider = FakeInsightProvider(
        result=make_insight_generation_result(supporting_run_ids=completed_ids, persona_count=2)
    )
    insights = InsightGenerationService(db_session, insight_provider).generate(
        project.id, experiment.id
    )

    # Missing uncertainty item -> rejected.
    candidate_missing_uncertainty = make_decision_memo_candidate(
        recommendation=Recommendation.ITERATE,
        executive_summary="Iterate: gather more signal before proceeding.",
        supporting_insight_ids=[i.id for i in insights],
        uncertain_conclusions=[],
    )
    with pytest.raises(ProviderError):
        DecisionMemoService(
            db_session, FakeDecisionMemoProvider(result=candidate_missing_uncertainty)
        ).generate(project.id, experiment.id)

    # Present but never mentions "evidence" anywhere -> still rejected.
    candidate_no_evidence_mention = make_decision_memo_candidate(
        recommendation=Recommendation.ITERATE,
        executive_summary="Iterate: gather more signal before proceeding.",
        supporting_insight_ids=[i.id for i in insights],
        uncertain_conclusions=["Model confidence is limited without more signal."],
        recommended_product_changes=["Clarify onboarding copy."],
        risks=["The concept may not resonate with the target segment."],
        real_user_test=make_real_user_test_plan(
            objective="Test the onboarding flow with participants."
        ),
    )
    with pytest.raises(ProviderError):
        DecisionMemoService(
            db_session, FakeDecisionMemoProvider(result=candidate_no_evidence_mention)
        ).generate(project.id, experiment.id)

    # Mentions evidence and includes an uncertainty item -> accepted.
    candidate_ok = make_decision_memo_candidate(
        recommendation=Recommendation.ITERATE,
        executive_summary="Iterate: gather more signal before proceeding.",
        supporting_insight_ids=[i.id for i in insights],
        uncertain_conclusions=["No completed runs cited supporting evidence."],
        recommended_product_changes=["Collect real evidence before further investment."],
    )
    memo = DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate_ok)).generate(
        project.id, experiment.id
    )
    assert memo.recommendation == Recommendation.ITERATE


def test_get_returns_404_when_no_memo_generated(db_session: Session) -> None:
    project, experiment, _insights = _seed_experiment_with_insights(db_session)
    with pytest.raises(NotFoundError):
        DecisionMemoService(db_session, FakeDecisionMemoProvider()).get(project.id, experiment.id)


def test_get_returns_persisted_memo(db_session: Session) -> None:
    project, experiment, insights = _seed_experiment_with_insights(db_session)
    candidate = make_decision_memo_candidate(supporting_insight_ids=[i.id for i in insights])
    service = DecisionMemoService(db_session, FakeDecisionMemoProvider(result=candidate))
    created = service.generate(project.id, experiment.id)

    fetched = service.get(project.id, experiment.id)
    assert fetched.id == created.id
