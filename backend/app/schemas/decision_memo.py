"""Pydantic schemas for the DecisionMemo API and for validating raw LLM output.

Two distinct validation boundaries live here, mirroring `app.schemas.insight`:

- `DecisionMemoCandidate` (and its nested `RealUserTestPlan`) validates the
  *raw, untrusted* JSON object parsed from the Decision Memo provider
  response, before anything is persisted. `supporting_insight_ids` is
  checked against `allowed_insight_ids` (the experiment's own persisted
  Insight IDs) passed via Pydantic's validation `context`, so a fabricated
  reference fails validation and the whole memo is rejected.
- `DecisionMemoRead` is the ordinary API-facing schema for an
  already-persisted memo.

Decision *safety* rules (Proceed must name real-user validation, severe
data-quality warnings block Proceed, forbidden market/launch-validation
language) are enforced in `app.services.decision_memo`, not here — they
depend on the experiment's deterministic analytics, which schema validation
alone cannot see.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app.models.decision_memo import Recommendation


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


def _normalize_int_list(values: list[int]) -> list[int]:
    """Drop duplicates, preserving first-occurrence order."""
    seen: set[int] = set()
    normalized: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


class RealUserTestPlan(BaseModel):
    """The proposed real-user follow-up experiment.

    Never implies that a specific participant count alone guarantees
    statistical validity — `sample_size_rationale` must instead explain why
    the proposed scope is appropriate for the next learning step.
    """

    objective: str
    target_participants: list[str]
    method: str
    sample_size_rationale: str
    tasks_or_questions: list[str]
    success_metrics: list[str]
    stopping_rule: str

    @field_validator("objective", "method", "sample_size_rationale", "stopping_rule")
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator("target_participants", "tasks_or_questions", "success_metrics")
    @classmethod
    def _normalize_and_require_lists(cls, value: list[str]) -> list[str]:
        normalized = _normalize_string_list(value)
        if not normalized:
            raise ValueError("must contain at least one non-blank item.")
        return normalized


class DecisionMemoCandidate(BaseModel):
    """The full, untrusted LLM response for a Decision Memo generation request."""

    recommendation: Recommendation
    executive_summary: str
    supporting_findings: list[str]
    weakest_assumptions: list[str]
    recommended_product_changes: list[str]
    risks: list[str]
    uncertain_conclusions: list[str] = Field(default_factory=list)
    recommended_success_metrics: list[str]
    real_user_test: RealUserTestPlan
    supporting_insight_ids: list[int]

    @field_validator("executive_summary")
    @classmethod
    def _trim_and_require_summary(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator(
        "supporting_findings",
        "weakest_assumptions",
        "recommended_product_changes",
        "risks",
        "recommended_success_metrics",
    )
    @classmethod
    def _normalize_and_require_lists(cls, value: list[str]) -> list[str]:
        normalized = _normalize_string_list(value)
        if not normalized:
            raise ValueError("must contain at least one non-blank item.")
        return normalized

    @field_validator("uncertain_conclusions")
    @classmethod
    def _normalize_uncertain_conclusions(cls, value: list[str]) -> list[str]:
        return _normalize_string_list(value)

    @field_validator("supporting_insight_ids")
    @classmethod
    def _normalize_insight_ids(cls, value: list[int]) -> list[int]:
        normalized = _normalize_int_list(value)
        if not normalized:
            raise ValueError("supporting_insight_ids must not be empty.")
        return normalized

    @model_validator(mode="after")
    def _validate_insight_references(self, info: ValidationInfo) -> "DecisionMemoCandidate":
        context = info.context or {}
        allowed_insight_ids: set[int] | None = context.get("allowed_insight_ids")
        if allowed_insight_ids is not None:
            invalid = [
                insight_id
                for insight_id in self.supporting_insight_ids
                if insight_id not in allowed_insight_ids
            ]
            if invalid:
                raise ValueError(
                    f"supporting_insight_ids references Insight(s) not belonging to "
                    f"this experiment: {invalid}"
                )
        return self


class DecisionMemoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    recommendation: Recommendation
    executive_summary: str
    supporting_findings: list[str]
    weakest_assumptions: list[str]
    recommended_product_changes: list[str]
    risks: list[str]
    uncertain_conclusions: list[str]
    recommended_success_metrics: list[str]
    real_user_test: RealUserTestPlan
    supporting_insight_ids: list[int]
    prompt_version: str
    model_name: str
    created_at: datetime
    updated_at: datetime
