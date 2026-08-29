"""Pydantic validation for raw, untrusted Insight-generation LLM output.

`InsightCandidate`/`InsightGenerationResult` are the local validation
boundary between the LLM provider and persistence — every scenario here
exercises `model_validate` directly, exactly as `OpenAIInsightProvider`
does with `json.loads`-parsed provider output.
"""

import pytest
from pydantic import ValidationError

from app.schemas.insight import InsightCandidate, InsightGenerationResult


def _candidate_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "category": "strength",
        "variant_scope": "both",
        "title": "Clear value proposition",
        "summary": "Personas found the value proposition clear.",
        "frequency": 2,
        "persona_count": 2,
        "supporting_run_ids": [1, 2],
        "supporting_evidence_ids": [10],
        "confidence_level": "medium",
    }
    payload.update(overrides)
    return payload


def _context(**overrides: object) -> dict:
    context: dict[str, object] = {
        "allowed_run_ids": {1, 2, 3},
        "run_evidence_ids": {1: {10}, 2: {10, 11}, 3: set()},
        "run_persona_ids": {1: 100, 2: 200, 3: 300},
    }
    context.update(overrides)
    return context


def test_valid_candidate_passes_validation() -> None:
    candidate = InsightCandidate.model_validate(_candidate_payload(), context=_context())
    assert candidate.title == "Clear value proposition"
    assert candidate.supporting_run_ids == [1, 2]
    assert candidate.persona_count == 2


def test_blank_title_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(_candidate_payload(title="   "), context=_context())


def test_blank_summary_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(_candidate_payload(summary=""), context=_context())


def test_invalid_category_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(
            _candidate_payload(category="not-a-real-category"), context=_context()
        )


def test_invalid_variant_scope_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(_candidate_payload(variant_scope="C"), context=_context())


def test_frequency_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(
            _candidate_payload(frequency=0, supporting_run_ids=[]), context=_context()
        )


def test_persona_count_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(_candidate_payload(persona_count=0), context=_context())


def test_supporting_run_ids_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(
            _candidate_payload(supporting_run_ids=[], frequency=0), context=_context()
        )


def test_supporting_run_ids_deduplicated() -> None:
    candidate = InsightCandidate.model_validate(
        _candidate_payload(supporting_run_ids=[1, 1, 2], frequency=2), context=_context()
    )
    assert candidate.supporting_run_ids == [1, 2]


def test_supporting_evidence_ids_deduplicated() -> None:
    candidate = InsightCandidate.model_validate(
        _candidate_payload(supporting_evidence_ids=[10, 10]), context=_context()
    )
    assert candidate.supporting_evidence_ids == [10]


def test_fabricated_run_id_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(
            _candidate_payload(supporting_run_ids=[1, 999], frequency=2), context=_context()
        )


def test_unsupported_evidence_reference_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(
            _candidate_payload(supporting_evidence_ids=[999]), context=_context()
        )


def test_incorrect_frequency_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(_candidate_payload(frequency=5), context=_context())


def test_incorrect_persona_count_rejected() -> None:
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(_candidate_payload(persona_count=5), context=_context())


def test_frequency_checked_even_without_context() -> None:
    # frequency vs. supporting_run_ids consistency is unconditional, unlike
    # the context-gated run/evidence reference checks.
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(_candidate_payload(frequency=5))


def test_generation_result_requires_at_least_one_insight() -> None:
    with pytest.raises(ValidationError):
        InsightGenerationResult.model_validate({"insights": []}, context=_context())


def test_generation_result_rejects_more_than_twelve_insights() -> None:
    insights = [
        _candidate_payload(title=f"Insight {i}", category="strength", variant_scope="both")
        for i in range(13)
    ]
    with pytest.raises(ValidationError):
        InsightGenerationResult.model_validate({"insights": insights}, context=_context())


def test_generation_result_accepts_twelve_insights() -> None:
    insights = [
        _candidate_payload(title=f"Insight {i}", category="strength", variant_scope="both")
        for i in range(12)
    ]
    result = InsightGenerationResult.model_validate({"insights": insights}, context=_context())
    assert len(result.insights) == 12


def test_duplicate_title_category_variant_rejected() -> None:
    insights = [_candidate_payload(), _candidate_payload()]
    with pytest.raises(ValidationError):
        InsightGenerationResult.model_validate({"insights": insights}, context=_context())


def test_duplicate_title_is_case_insensitive() -> None:
    insights = [
        _candidate_payload(title="Clear value proposition"),
        _candidate_payload(title="CLEAR VALUE PROPOSITION"),
    ]
    with pytest.raises(ValidationError):
        InsightGenerationResult.model_validate({"insights": insights}, context=_context())


def test_different_category_is_not_a_duplicate() -> None:
    insights = [
        _candidate_payload(category="strength"),
        _candidate_payload(category="objection"),
    ]
    result = InsightGenerationResult.model_validate({"insights": insights}, context=_context())
    assert len(result.insights) == 2


def test_one_invalid_candidate_rejects_entire_batch() -> None:
    insights = [
        _candidate_payload(title="Valid insight"),
        _candidate_payload(title="Invalid insight", supporting_run_ids=[1, 999], frequency=2),
    ]
    with pytest.raises(ValidationError):
        InsightGenerationResult.model_validate({"insights": insights}, context=_context())
