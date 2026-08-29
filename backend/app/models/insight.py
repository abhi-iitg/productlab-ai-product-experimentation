"""Insight domain model: one locally validated, evidence-linked qualitative
finding produced by LLM-assisted theme clustering over an Experiment's
completed simulation runs (Stage 6).

Insights are generated once per Experiment (duplicate generation is
rejected at the service layer) and are immutable once persisted — no
editing or deletion is exposed. Every `supporting_run_ids` entry must
reference a completed `SimulationRun` belonging to the same Experiment, and
every `supporting_evidence_ids` entry must have been actually cited by one
of those runs' validated evidence references; both are enforced by Pydantic
validation (see `app.schemas.insight`) before persistence, never here.
"""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.persona import ConfidenceLevel

if TYPE_CHECKING:
    from app.models.experiment import Experiment


class InsightCategory(enum.StrEnum):
    STRENGTH = "strength"
    OBJECTION = "objection"
    CONFUSION = "confusion"
    FEATURE_REQUEST = "feature_request"
    UNCERTAINTY = "uncertainty"
    DISAGREEMENT = "disagreement"


class VariantScope(enum.StrEnum):
    A = "A"
    B = "B"
    BOTH = "both"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "title",
            "category",
            "variant_scope",
            name="uq_insight_experiment_title_category_variant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[InsightCategory] = mapped_column(
        Enum(InsightCategory, native_enum=False, length=20), nullable=False
    )
    variant_scope: Mapped[VariantScope] = mapped_column(
        Enum(VariantScope, native_enum=False, length=4), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    persona_count: Mapped[int] = mapped_column(Integer, nullable=False)
    supporting_run_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    supporting_evidence_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    confidence_level: Mapped[ConfidenceLevel] = mapped_column(
        Enum(ConfidenceLevel, native_enum=False, length=10), nullable=False
    )
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    experiment: Mapped["Experiment"] = relationship(back_populates="insights")
