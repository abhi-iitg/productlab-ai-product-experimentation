"""Pydantic schemas for the Persona API and for validating raw LLM output.

Two distinct validation boundaries live here:

- `PersonaGenerationResult` (and its nested `GeneratedPersona` /
  `EvidenceReference`) validates the *raw, untrusted* JSON object parsed
  from the LLM provider response, before anything is persisted. Evidence
  references are checked against the `allowed_evidence_ids` passed via
  Pydantic's validation `context` — the set of evidence item IDs that were
  actually included in the generation context — so a persona citing an
  evidence ID it was never shown fails validation and the entire result is
  rejected (`PersonaService` never receives a partial/invalid result).
- `PersonaRead` / `PersonaGenerateRequest` / `PersonaGenerateResponse` are
  the ordinary API-facing schemas for already-persisted personas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app.models.persona import ConfidenceLevel


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


class EvidenceReference(BaseModel):
    evidence_item_id: int
    supported_claims: list[str]

    @field_validator("supported_claims")
    @classmethod
    def _normalize_claims(cls, value: list[str]) -> list[str]:
        normalized = _normalize_string_list(value)
        if not normalized:
            raise ValueError("supported_claims must contain at least one non-blank claim.")
        return normalized

    @model_validator(mode="after")
    def _check_allowed_evidence_id(self, info: ValidationInfo) -> "EvidenceReference":
        allowed_ids = (info.context or {}).get("allowed_evidence_ids") if info.context else None
        if allowed_ids is not None and self.evidence_item_id not in allowed_ids:
            raise ValueError(
                f"evidence_item_id {self.evidence_item_id} was not supplied in the "
                "generation context."
            )
        return self


class GeneratedPersona(BaseModel):
    """A single persona as validated from raw, untrusted LLM output."""

    name: str
    segment_label: str
    summary: str
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    behaviors: list[str] = Field(default_factory=list)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    unsupported_assumptions: list[str] = Field(default_factory=list)
    confidence_level: ConfidenceLevel

    @field_validator("name", "segment_label", "summary")
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator("goals", "pain_points", "constraints", "behaviors", "unsupported_assumptions")
    @classmethod
    def _normalize_lists(cls, value: list[str]) -> list[str]:
        return _normalize_string_list(value)

    @field_validator("evidence_references")
    @classmethod
    def _require_evidence_references(
        cls, value: list[EvidenceReference]
    ) -> list[EvidenceReference]:
        if not value:
            raise ValueError("evidence_references must not be empty; personas must be grounded.")
        return value


class PersonaGenerationResult(BaseModel):
    """The full, untrusted LLM response for a persona-generation request."""

    personas: list[GeneratedPersona]

    @field_validator("personas")
    @classmethod
    def _require_personas(cls, value: list[GeneratedPersona]) -> list[GeneratedPersona]:
        if not value:
            raise ValueError("personas must not be empty.")
        return value


class PersonaGenerateRequest(BaseModel):
    persona_count: int = Field(ge=2, le=5)
    selected_evidence_ids: list[int] | None = None
    focus: str | None = None

    @field_validator("selected_evidence_ids")
    @classmethod
    def _validate_selected_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if len(value) == 0:
            raise ValueError("selected_evidence_ids must not be empty when provided.")
        if len(set(value)) != len(value):
            raise ValueError("selected_evidence_ids must not contain duplicate IDs.")
        return value

    @field_validator("focus")
    @classmethod
    def _trim_focus(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class PersonaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    segment_label: str
    summary: str
    goals: list[str]
    pain_points: list[str]
    constraints: list[str]
    behaviors: list[str]
    evidence_references: list[EvidenceReference]
    unsupported_assumptions: list[str]
    confidence_level: ConfidenceLevel
    prompt_version: str
    model_name: str
    created_at: datetime
    updated_at: datetime


class PersonaGenerateResponse(BaseModel):
    project_id: int
    prompt_version: str
    model_name: str
    persona_count: int
    personas: list[PersonaRead]
