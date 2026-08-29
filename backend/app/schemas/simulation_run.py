"""Pydantic schemas for the SimulationRun API and for validating raw LLM output.

Two distinct validation boundaries live here, mirroring `app.schemas.persona`:

- `SimulationOutput` validates the *raw, untrusted* JSON object parsed from
  the simulation provider response, before anything is persisted. Evidence
  references are checked against `allowed_evidence_ids` passed via
  Pydantic's validation `context` — the evidence IDs actually attached to
  the persona being simulated — so a run citing an evidence ID the persona
  was never grounded in fails validation and the run is persisted as a
  failed run, not a partial success.
- `SimulationCallResult` wraps a validated `SimulationOutput` with the
  provider usage/latency metadata captured for that call; both token counts
  and latency are constrained non-negative here so a negative value can
  never reach persistence.
- `SimulationRunRead` is the ordinary API-facing schema for a persisted run.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.simulation_run import FailureType, SimulationRunStatus, TaskOutcome
from app.schemas.persona import EvidenceReference


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


class SimulationOutput(BaseModel):
    """The full, untrusted LLM response for a single simulation run."""

    task_outcome: TaskOutcome
    clarity_score: int = Field(ge=1, le=5)
    perceived_value_score: int = Field(ge=1, le=5)
    adoption_intent_score: int = Field(ge=1, le=5)
    response_summary: str
    positive_signals: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    confusion_points: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)

    @field_validator("response_summary")
    @classmethod
    def _trim_and_require_summary(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator(
        "positive_signals",
        "objections",
        "confusion_points",
        "feature_requests",
        "uncertainty_notes",
    )
    @classmethod
    def _normalize_lists(cls, value: list[str]) -> list[str]:
        return _normalize_string_list(value)


class SimulationCallResult(BaseModel):
    """Validated simulation output plus provider usage metadata for one call."""

    output: SimulationOutput
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int = Field(ge=0)


class SimulationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    variant_id: int
    persona_id: int
    repetition_index: int
    status: SimulationRunStatus
    task_outcome: TaskOutcome | None
    clarity_score: int | None
    perceived_value_score: int | None
    adoption_intent_score: int | None
    response_summary: str | None
    positive_signals: list[str]
    objections: list[str]
    confusion_points: list[str]
    feature_requests: list[str]
    uncertainty_notes: list[str]
    evidence_references: list[EvidenceReference]
    prompt_version: str
    model_name: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    estimated_cost_usd: Decimal | None
    failure_type: FailureType | None
    failure_message: str | None
    created_at: datetime
    completed_at: datetime | None
