"""SimulationRun domain model: one persona x variant x repetition result.

Stores either a completed, schema-validated structured result or a failed
run recording only a safe failure category and safe message — never raw
prompts, evidence content, provider response bodies, or stack traces.
"""

import enum
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.experiment import Experiment
    from app.models.persona import Persona
    from app.models.variant import Variant


class SimulationRunStatus(enum.StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class TaskOutcome(enum.StrEnum):
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


class FailureType(enum.StrEnum):
    CONFIGURATION_ERROR = "configuration_error"
    CONTEXT_LIMIT = "context_limit"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    PROVIDER_ERROR = "provider_error"
    EMPTY_OUTPUT = "empty_output"
    MALFORMED_JSON = "malformed_json"
    INVALID_SCHEMA = "invalid_schema"
    INVALID_EVIDENCE_REFERENCE = "invalid_evidence_reference"
    UNEXPECTED_ERROR = "unexpected_error"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "variant_id",
            "persona_id",
            "repetition_index",
            name="uq_simulation_run_matrix",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id", ondelete="CASCADE"), nullable=False
    )
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id"), nullable=False)
    repetition_index: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[SimulationRunStatus] = mapped_column(
        Enum(SimulationRunStatus, native_enum=False, length=10), nullable=False
    )

    # Successful-run fields (null for failed runs).
    task_outcome: Mapped[TaskOutcome | None] = mapped_column(
        Enum(TaskOutcome, native_enum=False, length=20), nullable=True
    )
    clarity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    perceived_value_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adoption_intent_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    positive_signals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    objections: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    confusion_points: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    feature_requests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    uncertainty_notes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence_references: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)

    # Metadata persisted for both completed and failed runs.
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)

    # Failed-run fields (null for completed runs). Safe category + safe
    # message only — never provider response bodies or stack traces.
    failure_type: Mapped[FailureType | None] = mapped_column(
        Enum(FailureType, native_enum=False, length=30), nullable=True
    )
    failure_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment: Mapped["Experiment"] = relationship(back_populates="runs")
    variant: Mapped["Variant"] = relationship()
    persona: Mapped["Persona"] = relationship()
