"""Pydantic schemas for the HumanFeedback API.

Plain CRUD schemas over an already-defined, deterministic domain model —
no LLM output validation boundary here (unlike `app.schemas.insight` or
`app.schemas.simulation_run`). `HumanFeedbackCreate`/`HumanFeedbackUpdate`
trim and validate every field a PM types in directly; `HumanFeedbackRead`
is the plain API-facing view of an already-persisted row.
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.human_feedback import HumanFeedbackSourceMethod
from app.models.simulation_run import TaskOutcome
from app.models.variant import VariantKey

_QUALITATIVE_FIELDS = (
    "positive_signals",
    "objections",
    "confusion_points",
    "feature_requests",
    "uncertainty_notes",
)


def _trim_required(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("must not be blank")
    return trimmed


def _normalize_string_list(values: list[str]) -> list[str]:
    """Trim, drop blanks, and drop duplicates (case-insensitive)."""
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        trimmed = value.strip()
        if not trimmed:
            continue
        key = trimmed.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(trimmed)
    return normalized


class HumanFeedbackCreate(BaseModel):
    participant_label: str
    variant_key: VariantKey
    source_method: HumanFeedbackSourceMethod
    session_date: date | None = None
    task_outcome: TaskOutcome
    clarity_score: int = Field(ge=1, le=5)
    perceived_value_score: int = Field(ge=1, le=5)
    adoption_intent_score: int = Field(ge=1, le=5)
    feedback_summary: str
    positive_signals: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    confusion_points: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)

    @field_validator("participant_label", "feedback_summary")
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator(*_QUALITATIVE_FIELDS)
    @classmethod
    def _normalize_lists(cls, value: list[str]) -> list[str]:
        return _normalize_string_list(value)


class HumanFeedbackUpdate(BaseModel):
    participant_label: str | None = None
    variant_key: VariantKey | None = None
    source_method: HumanFeedbackSourceMethod | None = None
    session_date: date | None = None
    task_outcome: TaskOutcome | None = None
    clarity_score: int | None = Field(default=None, ge=1, le=5)
    perceived_value_score: int | None = Field(default=None, ge=1, le=5)
    adoption_intent_score: int | None = Field(default=None, ge=1, le=5)
    feedback_summary: str | None = None
    positive_signals: list[str] | None = None
    objections: list[str] | None = None
    confusion_points: list[str] | None = None
    feature_requests: list[str] | None = None
    uncertainty_notes: list[str] | None = None

    @field_validator("participant_label", "feedback_summary")
    @classmethod
    def _trim_and_require(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _trim_required(value)

    @field_validator(*_QUALITATIVE_FIELDS)
    @classmethod
    def _normalize_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_string_list(value)

    @model_validator(mode="after")
    def _reject_empty_patch(self) -> "HumanFeedbackUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class HumanFeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    participant_label: str
    variant_key: VariantKey
    task_outcome: TaskOutcome
    clarity_score: int
    perceived_value_score: int
    adoption_intent_score: int
    feedback_summary: str
    positive_signals: list[str]
    objections: list[str]
    confusion_points: list[str]
    feature_requests: list[str]
    uncertainty_notes: list[str]
    source_method: HumanFeedbackSourceMethod
    session_date: date | None
    created_at: datetime
    updated_at: datetime
