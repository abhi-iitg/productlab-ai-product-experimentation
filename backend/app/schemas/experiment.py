"""Pydantic schemas for the Experiment/Variant API.

`ExperimentCreate`/`ExperimentUpdate` validate the nested creation/edit
request (variants, persona IDs, evaluation criteria); `ExperimentRead`/
`VariantRead` are the ordinary API-facing read schemas.
`ExperimentExecuteRequest` requires explicit confirmation before any
provider call is made, and `ExperimentExecutionSummary` is the safe,
validated response returned from execution — no raw prompts or provider
output.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.experiment import ExperimentStatus
from app.models.variant import VariantKey


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


def _validate_variant_pair(value: list["VariantCreate"]) -> list["VariantCreate"]:
    if len(value) != 2:
        raise ValueError("Exactly two variants are required.")
    keys = {variant.key for variant in value}
    if keys != {VariantKey.A, VariantKey.B}:
        raise ValueError("Exactly one Variant A and one Variant B are required.")
    return value


def _validate_persona_ids(value: list[int]) -> list[int]:
    if not value:
        raise ValueError("persona_ids must not be empty.")
    if len(set(value)) != len(value):
        raise ValueError("persona_ids must not contain duplicate IDs.")
    return value


class VariantCreate(BaseModel):
    key: VariantKey
    name: str
    description: str

    @field_validator("name", "description")
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        return _trim_required(value)


class ExperimentCreate(BaseModel):
    name: str
    objective: str
    hypothesis: str
    scenario: str
    evaluation_criteria: list[str]
    repeat_count: int = Field(ge=1, le=3)
    persona_ids: list[int]
    variants: list[VariantCreate]

    @field_validator("name", "objective", "hypothesis", "scenario")
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator("evaluation_criteria")
    @classmethod
    def _normalize_criteria(cls, value: list[str]) -> list[str]:
        normalized = _normalize_string_list(value)
        if not normalized:
            raise ValueError("evaluation_criteria must contain at least one item.")
        return normalized

    @field_validator("persona_ids")
    @classmethod
    def _check_persona_ids(cls, value: list[int]) -> list[int]:
        return _validate_persona_ids(value)

    @field_validator("variants")
    @classmethod
    def _check_variants(cls, value: list[VariantCreate]) -> list[VariantCreate]:
        return _validate_variant_pair(value)


class ExperimentUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    hypothesis: str | None = None
    scenario: str | None = None
    evaluation_criteria: list[str] | None = None
    repeat_count: int | None = Field(default=None, ge=1, le=3)
    persona_ids: list[int] | None = None
    variants: list[VariantCreate] | None = None

    @field_validator("name", "objective", "hypothesis", "scenario")
    @classmethod
    def _trim_and_require(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _trim_required(value)

    @field_validator("evaluation_criteria")
    @classmethod
    def _normalize_criteria(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = _normalize_string_list(value)
        if not normalized:
            raise ValueError("evaluation_criteria must contain at least one item.")
        return normalized

    @field_validator("persona_ids")
    @classmethod
    def _check_persona_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        return _validate_persona_ids(value)

    @field_validator("variants")
    @classmethod
    def _check_variants(cls, value: list[VariantCreate] | None) -> list[VariantCreate] | None:
        if value is None:
            return None
        return _validate_variant_pair(value)

    @model_validator(mode="after")
    def _reject_empty_patch(self) -> "ExperimentUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    key: VariantKey
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class ExperimentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    objective: str
    hypothesis: str
    scenario: str
    evaluation_criteria: list[str]
    repeat_count: int
    status: ExperimentStatus
    persona_ids: list[int]
    variants: list[VariantRead]
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ExperimentExecuteRequest(BaseModel):
    confirm_execution: bool

    @field_validator("confirm_execution")
    @classmethod
    def _require_true(cls, value: bool) -> bool:
        if not value:
            raise ValueError("confirm_execution must be true to start execution.")
        return value


class ExperimentExecutionSummary(BaseModel):
    project_id: int
    experiment_id: int
    status: ExperimentStatus
    total_runs: int
    completed_runs: int
    failed_runs: int
    prompt_version: str
    model_name: str
    started_at: datetime | None
    completed_at: datetime | None
