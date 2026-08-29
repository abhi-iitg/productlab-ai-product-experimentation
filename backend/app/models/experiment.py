"""Experiment domain model: a controlled two-variant simulation experiment.

An `Experiment` belongs to one `Project`, owns exactly two `Variant`s (A and
B, enforced at the schema/service layer — see `app/schemas/experiment.py`),
and references a fixed set of previously generated `Persona`s via the
`experiment_personas` association table so the selected persona set is
reproducible even if the project's persona library later grows.
"""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.decision_memo import DecisionMemo
    from app.models.human_feedback import HumanFeedback
    from app.models.insight import Insight
    from app.models.persona import Persona
    from app.models.project import Project
    from app.models.simulation_run import SimulationRun
    from app.models.variant import Variant


class ExperimentStatus(enum.StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


def _utcnow() -> datetime:
    return datetime.now(UTC)


# Plain association table (not a mapped class): preserves the persona set
# selected for an experiment. SQLAlchemy automatically maintains rows here
# as `Experiment.personas` is assigned/mutated, and removes matching rows
# when the owning Experiment is deleted.
experiment_personas = Table(
    "experiment_personas",
    Base.metadata,
    Column("experiment_id", ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True),
    Column("persona_id", ForeignKey("personas.id", ondelete="CASCADE"), primary_key=True),
)


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_criteria: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    repeat_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus, native_enum=False, length=20),
        nullable=False,
        default=ExperimentStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="experiments")
    variants: Mapped[list["Variant"]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="Variant.key",
    )
    runs: Mapped[list["SimulationRun"]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="SimulationRun.id",
    )
    personas: Mapped[list["Persona"]] = relationship(
        secondary=experiment_personas, order_by="Persona.id"
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="Insight.id",
    )
    decision_memo: Mapped["DecisionMemo | None"] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        uselist=False,
    )
    human_feedback: Mapped[list["HumanFeedback"]] = relationship(
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="HumanFeedback.id",
    )

    @property
    def persona_ids(self) -> list[int]:
        return [persona.id for persona in self.personas]
