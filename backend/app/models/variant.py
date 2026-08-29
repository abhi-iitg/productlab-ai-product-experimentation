"""Variant domain model: one of the two product concepts in an Experiment."""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.experiment import Experiment


class VariantKey(enum.StrEnum):
    A = "A"
    B = "B"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Variant(Base):
    __tablename__ = "variants"
    __table_args__ = (UniqueConstraint("experiment_id", "key", name="uq_variant_experiment_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[VariantKey] = mapped_column(
        Enum(VariantKey, native_enum=False, length=1), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    experiment: Mapped["Experiment"] = relationship(back_populates="variants")
