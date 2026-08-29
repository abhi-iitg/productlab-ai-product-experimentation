"""Project domain model: one product-discovery workspace and its brief."""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.evidence_item import EvidenceItem
    from app.models.experiment import Experiment
    from app.models.persona import Persona


class ProjectStatus(enum.StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    target_user: Mapped[str] = mapped_column(Text, nullable=False)
    product_hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    success_metric: Mapped[str] = mapped_column(Text, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=20),
        nullable=False,
        default=ProjectStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    evidence_items: Mapped[list["EvidenceItem"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="EvidenceItem.id",
    )
    personas: Mapped[list["Persona"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Persona.id",
    )
    experiments: Mapped[list["Experiment"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Experiment.id",
    )
