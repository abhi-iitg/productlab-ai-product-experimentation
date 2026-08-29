"""Pydantic validation for raw, untrusted Decision Memo LLM output.

`DecisionMemoCandidate`/`RealUserTestPlan` are the local validation
boundary between the LLM provider and persistence — every scenario here
exercises `model_validate` directly, exactly as `OpenAIDecisionMemoProvider`
does with `json.loads`-parsed provider output. Decision *safety* rules
(forbidden market-validation language, Proceed requiring real-user
validation language, etc.) are tested in `test_decision_memo_service.py`,
since they depend on deterministic analytics the schema alone can't see.
"""

import pytest
from pydantic import ValidationError

from app.schemas.decision_memo import DecisionMemoCandidate, RealUserTestPlan


def _real_user_test_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "objective": "Validate whether real users complete setup unaided.",
        "target_participants": ["5-8 early-stage product managers."],
        "method": "Moderated usability test.",
        "sample_size_rationale": "Sufficient to surface major usability blockers.",
        "tasks_or_questions": ["Complete setup unaided."],
        "success_metrics": ["Setup completion rate."],
        "stopping_rule": "Stop after 5 sessions if the same blocker recurs.",
    }
    payload.update(overrides)
    return payload


def _candidate_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "recommendation": "proceed",
        "executive_summary": "Signal is strong; recommend real-user validation next.",
        "supporting_findings": ["Personas understood the value proposition."],
        "weakest_assumptions": ["Assumes unaided discovery."],
        "recommended_product_changes": ["Add an inline hint."],
        "risks": ["Evidence library is thin."],
        "uncertain_conclusions": ["Moderate confidence on adoption intent."],
        "recommended_success_metrics": ["Setup completion rate."],
        "real_user_test": _real_user_test_payload(),
        "supporting_insight_ids": [1, 2],
    }
    payload.update(overrides)
    return payload


def test_valid_real_user_test_plan_passes_validation() -> None:
    plan = RealUserTestPlan.model_validate(_real_user_test_payload())
    assert plan.objective
    assert plan.target_participants


def test_real_user_test_blank_objective_rejected() -> None:
    with pytest.raises(ValidationError):
        RealUserTestPlan.model_validate(_real_user_test_payload(objective="   "))


def test_real_user_test_empty_target_participants_rejected() -> None:
    with pytest.raises(ValidationError):
        RealUserTestPlan.model_validate(_real_user_test_payload(target_participants=[]))


def test_real_user_test_lists_are_normalized() -> None:
    plan = RealUserTestPlan.model_validate(
        _real_user_test_payload(success_metrics=["Rate", "rate", " Rate "])
    )
    assert plan.success_metrics == ["Rate"]


def test_valid_candidate_passes_validation() -> None:
    candidate = DecisionMemoCandidate.model_validate(
        _candidate_payload(), context={"allowed_insight_ids": {1, 2}}
    )
    assert candidate.recommendation.value == "proceed"
    assert candidate.supporting_insight_ids == [1, 2]


def test_invalid_recommendation_rejected() -> None:
    with pytest.raises(ValidationError):
        DecisionMemoCandidate.model_validate(
            _candidate_payload(recommendation="launch"), context={"allowed_insight_ids": {1, 2}}
        )


def test_blank_executive_summary_rejected() -> None:
    with pytest.raises(ValidationError):
        DecisionMemoCandidate.model_validate(
            _candidate_payload(executive_summary="   "), context={"allowed_insight_ids": {1, 2}}
        )


@pytest.mark.parametrize(
    "field",
    [
        "supporting_findings",
        "weakest_assumptions",
        "recommended_product_changes",
        "risks",
        "recommended_success_metrics",
    ],
)
def test_required_list_fields_reject_empty(field: str) -> None:
    with pytest.raises(ValidationError):
        DecisionMemoCandidate.model_validate(
            _candidate_payload(**{field: []}), context={"allowed_insight_ids": {1, 2}}
        )


def test_uncertain_conclusions_may_be_empty() -> None:
    candidate = DecisionMemoCandidate.model_validate(
        _candidate_payload(uncertain_conclusions=[]), context={"allowed_insight_ids": {1, 2}}
    )
    assert candidate.uncertain_conclusions == []


def test_supporting_insight_ids_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        DecisionMemoCandidate.model_validate(
            _candidate_payload(supporting_insight_ids=[]), context={"allowed_insight_ids": {1, 2}}
        )


def test_supporting_insight_ids_deduplicated() -> None:
    candidate = DecisionMemoCandidate.model_validate(
        _candidate_payload(supporting_insight_ids=[1, 1, 2]),
        context={"allowed_insight_ids": {1, 2}},
    )
    assert candidate.supporting_insight_ids == [1, 2]


def test_fabricated_insight_id_rejected() -> None:
    with pytest.raises(ValidationError):
        DecisionMemoCandidate.model_validate(
            _candidate_payload(supporting_insight_ids=[1, 999]),
            context={"allowed_insight_ids": {1, 2}},
        )


def test_cross_experiment_insight_id_rejected() -> None:
    # allowed_insight_ids models "this experiment's own Insight IDs";
    # referencing an ID outside that set (e.g. from another experiment)
    # fails the same reference check as a fabricated ID.
    with pytest.raises(ValidationError):
        DecisionMemoCandidate.model_validate(
            _candidate_payload(supporting_insight_ids=[42]),
            context={"allowed_insight_ids": {1, 2}},
        )


def test_no_context_skips_reference_check() -> None:
    candidate = DecisionMemoCandidate.model_validate(
        _candidate_payload(supporting_insight_ids=[123456])
    )
    assert candidate.supporting_insight_ids == [123456]
