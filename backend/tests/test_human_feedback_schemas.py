"""Pydantic schema validation for HumanFeedback."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.human_feedback import HumanFeedbackCreate, HumanFeedbackUpdate


def _valid_payload(**overrides: object) -> dict:
    payload: dict[str, object] = {
        "participant_label": "Participant 1",
        "variant_key": "A",
        "source_method": "usability_test",
        "task_outcome": "completed",
        "clarity_score": 4,
        "perceived_value_score": 5,
        "adoption_intent_score": 4,
        "feedback_summary": "The participant completed the task with minimal confusion.",
        "positive_signals": ["Liked the guided steps", " liked the guided steps "],
        "objections": [],
        "confusion_points": [],
        "feature_requests": [],
        "uncertainty_notes": [],
    }
    payload.update(overrides)
    return payload


def test_human_feedback_create_valid_payload() -> None:
    feedback = HumanFeedbackCreate(**_valid_payload())
    assert feedback.participant_label == "Participant 1"
    assert feedback.variant_key.value == "A"
    assert feedback.task_outcome.value == "completed"
    assert feedback.session_date is None


def test_human_feedback_create_trims_participant_label_and_summary() -> None:
    feedback = HumanFeedbackCreate(
        **_valid_payload(participant_label="  Participant 1  ", feedback_summary="  Summary.  ")
    )
    assert feedback.participant_label == "Participant 1"
    assert feedback.feedback_summary == "Summary."


def test_human_feedback_create_rejects_blank_participant_label() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackCreate(**_valid_payload(participant_label="   "))


def test_human_feedback_create_rejects_blank_summary() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackCreate(**_valid_payload(feedback_summary="   "))


def test_human_feedback_create_rejects_invalid_variant_key() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackCreate(**_valid_payload(variant_key="C"))


def test_human_feedback_create_rejects_invalid_task_outcome() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackCreate(**_valid_payload(task_outcome="not_a_real_outcome"))


def test_human_feedback_create_rejects_invalid_source_method() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackCreate(**_valid_payload(source_method="focus_group"))


@pytest.mark.parametrize(
    "field", ["clarity_score", "perceived_value_score", "adoption_intent_score"]
)
@pytest.mark.parametrize("value", [0, 6])
def test_human_feedback_create_scores_are_constrained_between_one_and_five(
    field: str, value: int
) -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackCreate(**_valid_payload(**{field: value}))


@pytest.mark.parametrize(
    "field", ["clarity_score", "perceived_value_score", "adoption_intent_score"]
)
@pytest.mark.parametrize("value", [1, 5])
def test_human_feedback_create_scores_accept_boundary_values(field: str, value: int) -> None:
    feedback = HumanFeedbackCreate(**_valid_payload(**{field: value}))
    assert getattr(feedback, field) == value


def test_human_feedback_create_normalizes_qualitative_lists() -> None:
    feedback = HumanFeedbackCreate(**_valid_payload())
    # Trimmed and deduplicated case-insensitively; blank entries dropped.
    assert feedback.positive_signals == ["Liked the guided steps"]


def test_human_feedback_create_drops_blank_qualitative_entries() -> None:
    feedback = HumanFeedbackCreate(**_valid_payload(objections=["Confusing copy", "  ", ""]))
    assert feedback.objections == ["Confusing copy"]


def test_human_feedback_create_qualitative_lists_default_to_empty() -> None:
    payload = _valid_payload()
    for field in (
        "positive_signals",
        "objections",
        "confusion_points",
        "feature_requests",
        "uncertainty_notes",
    ):
        payload.pop(field)
    feedback = HumanFeedbackCreate(**payload)
    assert feedback.objections == []
    assert feedback.confusion_points == []


def test_human_feedback_create_accepts_optional_session_date() -> None:
    feedback = HumanFeedbackCreate(**_valid_payload(session_date="2026-07-15"))
    assert feedback.session_date == date(2026, 7, 15)


def test_human_feedback_create_session_date_serializes_as_iso_date() -> None:
    feedback = HumanFeedbackCreate(**_valid_payload(session_date="2026-07-15"))
    dumped = feedback.model_dump(mode="json")
    assert dumped["session_date"] == "2026-07-15"


def test_human_feedback_update_rejects_empty_patch() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackUpdate()


def test_human_feedback_update_allows_single_field() -> None:
    update = HumanFeedbackUpdate(feedback_summary="Updated summary.")
    assert update.feedback_summary == "Updated summary."
    assert update.participant_label is None


def test_human_feedback_update_rejects_blank_provided_participant_label() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackUpdate(participant_label="   ")


def test_human_feedback_update_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        HumanFeedbackUpdate(clarity_score=6)


def test_human_feedback_update_normalizes_qualitative_lists_when_provided() -> None:
    update = HumanFeedbackUpdate(objections=["Slow load time", "slow load time "])
    assert update.objections == ["Slow load time"]


def test_human_feedback_update_has_no_experiment_id_field() -> None:
    assert "experiment_id" not in HumanFeedbackUpdate.model_fields


def test_human_feedback_update_allows_explicit_none_for_other_fields() -> None:
    update = HumanFeedbackUpdate(
        feedback_summary="Updated summary.", participant_label=None, objections=None
    )
    assert update.feedback_summary == "Updated summary."
    assert update.participant_label is None
    assert update.objections is None
