"""Pydantic schemas for the EvidenceItem API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.evidence_item import EvidenceType


def _trim_required(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("must not be blank")
    return trimmed


def _trim_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


class EvidenceItemCreate(BaseModel):
    evidence_type: EvidenceType
    title: str
    content: str
    source_label: str | None = None

    @field_validator("title", "content")
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator("source_label")
    @classmethod
    def _trim_source_label(cls, value: str | None) -> str | None:
        return _trim_optional(value)


class EvidenceItemUpdate(BaseModel):
    evidence_type: EvidenceType | None = None
    title: str | None = None
    content: str | None = None
    source_label: str | None = None

    @field_validator("title", "content")
    @classmethod
    def _trim_and_require(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _trim_required(value)

    @field_validator("source_label")
    @classmethod
    def _trim_source_label(cls, value: str | None) -> str | None:
        return _trim_optional(value)

    @model_validator(mode="after")
    def _reject_empty_patch(self) -> "EvidenceItemUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class EvidenceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    evidence_type: EvidenceType
    title: str
    content: str
    source_label: str | None
    created_at: datetime
    updated_at: datetime
