"""Pydantic schemas for the Insight API and for validating raw LLM output.

Two distinct validation boundaries live here, mirroring `app.schemas.persona`
and `app.schemas.simulation_run`:

- `InsightGenerationResult` (and its nested `InsightCandidate`) validates
  the *raw, untrusted* JSON object parsed from the Insight provider
  response, before anything is persisted. Every `supporting_run_ids` entry
  is checked against `allowed_run_ids` (the experiment's completed run
  IDs), every `supporting_evidence_ids` entry is checked against the union
  of evidence IDs actually cited by its own `supporting_run_ids`, and
  `frequency`/`persona_count` are checked against the referenced runs —
  all passed via Pydantic's validation `context` — so a fabricated
  reference or an inconsistent count fails validation and the entire batch
  is rejected (`InsightGenerationService` never persists a partial batch).
- `InsightRead` is the ordinary API-facing schema for an already-persisted
  Insight.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from app.models.insight import InsightCategory, VariantScope
from app.models.persona import ConfidenceLevel

_MIN_INSIGHTS = 1
_MAX_INSIGHTS = 12


def _trim_required(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("must not be blank")
    return trimmed


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


class InsightCandidate(BaseModel):
    """A single insight as validated from raw, untrusted LLM output."""

    category: InsightCategory
    variant_scope: VariantScope
    title: str
    summary: str
    frequency: int = Field(gt=0)
    persona_count: int = Field(gt=0)
    supporting_run_ids: list[int]
    supporting_evidence_ids: list[int] = Field(default_factory=list)
    confidence_level: ConfidenceLevel

    @field_validator("title", "summary")
    @classmethod
    def _trim_and_require(cls, value: str) -> str:
        return _trim_required(value)

    @field_validator("supporting_run_ids")
    @classmethod
    def _normalize_run_ids(cls, value: list[int]) -> list[int]:
        normalized = _normalize_int_list(value)
        if not normalized:
            raise ValueError("supporting_run_ids must not be empty.")
        return normalized

    @field_validator("supporting_evidence_ids")
    @classmethod
    def _normalize_evidence_ids(cls, value: list[int]) -> list[int]:
        return _normalize_int_list(value)

    @model_validator(mode="after")
    def _validate_references_and_counts(self, info: ValidationInfo) -> "InsightCandidate":
        context = info.context or {}
        allowed_run_ids: set[int] | None = context.get("allowed_run_ids")
        run_evidence_ids: dict[int, set[int]] = context.get("run_evidence_ids", {})
        run_persona_ids: dict[int, int] = context.get("run_persona_ids", {})

        if allowed_run_ids is not None:
            invalid_runs = [rid for rid in self.supporting_run_ids if rid not in allowed_run_ids]
            if invalid_runs:
                raise ValueError(
                    f"supporting_run_ids references run(s) not eligible for this "
                    f"experiment: {invalid_runs}"
                )

        if self.supporting_evidence_ids:
            cited_union: set[int] = set()
            for run_id in self.supporting_run_ids:
                cited_union |= run_evidence_ids.get(run_id, set())
            invalid_evidence = [
                eid for eid in self.supporting_evidence_ids if eid not in cited_union
            ]
            if invalid_evidence:
                raise ValueError(
                    f"supporting_evidence_ids references evidence not cited by any "
                    f"supporting run: {invalid_evidence}"
                )

        if self.frequency != len(self.supporting_run_ids):
            raise ValueError("frequency must equal the number of supporting_run_ids.")

        if run_persona_ids:
            distinct_personas = {
                run_persona_ids[rid] for rid in self.supporting_run_ids if rid in run_persona_ids
            }
            if self.persona_count != len(distinct_personas):
                raise ValueError(
                    "persona_count must equal the number of distinct personas among "
                    "supporting_run_ids."
                )

        return self


class InsightGenerationResult(BaseModel):
    """The full, untrusted LLM response for an Insight-generation request."""

    insights: list[InsightCandidate] = Field(min_length=_MIN_INSIGHTS, max_length=_MAX_INSIGHTS)

    @model_validator(mode="after")
    def _require_unique_combinations(self) -> "InsightGenerationResult":
        seen: set[tuple[str, InsightCategory, VariantScope]] = set()
        for insight in self.insights:
            key = (insight.title.casefold(), insight.category, insight.variant_scope)
            if key in seen:
                raise ValueError(
                    "Duplicate title/category/variant_scope combination in insights: "
                    f"{insight.title!r}."
                )
            seen.add(key)
        return self


class InsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_id: int
    category: InsightCategory
    variant_scope: VariantScope
    title: str
    summary: str
    frequency: int
    persona_count: int
    supporting_run_ids: list[int]
    supporting_evidence_ids: list[int]
    confidence_level: ConfidenceLevel
    prompt_version: str
    model_name: str
    created_at: datetime


class InsightGenerateResponse(BaseModel):
    experiment_id: int
    prompt_version: str
    model_name: str
    insight_count: int
    insights: list[InsightRead]
