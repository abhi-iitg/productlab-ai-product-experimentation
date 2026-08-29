"""Pydantic schemas for the Project API (product brief)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.project import ProjectStatus

_REQUIRED_TEXT_FIELDS = (
    "name",
    "problem_statement",
    "target_user",
    "product_hypothesis",
    "success_metric",
)


def _normalize_assumptions(values: list[str]) -> list[str]:
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


class ProjectCreate(BaseModel):
    name: str
    problem_statement: str
    target_user: str
    product_hypothesis: str
    success_metric: str
    assumptions: list[str] = Field(default_factory=list)
    status: ProjectStatus = ProjectStatus.DRAFT

    @field_validator(*_REQUIRED_TEXT_FIELDS)
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed

    @field_validator("assumptions")
    @classmethod
    def _normalize(cls, value: list[str]) -> list[str]:
        return _normalize_assumptions(value)


class ProjectUpdate(BaseModel):
    name: str | None = None
    problem_statement: str | None = None
    target_user: str | None = None
    product_hypothesis: str | None = None
    success_metric: str | None = None
    assumptions: list[str] | None = None
    status: ProjectStatus | None = None

    @field_validator(*_REQUIRED_TEXT_FIELDS)
    @classmethod
    def _trim_and_require(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be blank")
        return trimmed

    @field_validator("assumptions")
    @classmethod
    def _normalize(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return _normalize_assumptions(value)

    @model_validator(mode="after")
    def _reject_empty_patch(self) -> "ProjectUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    problem_statement: str
    target_user: str
    product_hypothesis: str
    success_metric: str
    assumptions: list[str]
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
