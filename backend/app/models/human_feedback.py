"""HumanFeedback domain model: anonymized, manually entered real-participant
feedback for one Experiment (Stage 8).

`HumanFeedback` is deliberately editable and deletable — unlike `Insight`,
manually entered research data may need correction after the fact. It
reuses `VariantKey` (from `app.models.variant`) and `TaskOutcome` (from
`app.models.simulation_run`) rather than redefining them, so a feedback
record's `variant_key`/`task_outcome` carry the exact same meaning as the
synthetic side they're compared against. No PII fields, no AI-generated
fields, and no raw audio/video/file/transcript storage are permitted here
— only a pseudonymous `participant_label` and structured qualitative/
quantitative fields the PM types in directly.
"""

import enum
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.simulation_run import TaskOutcome
from app.models.variant import VariantKey

if TYPE_CHECKING:
    from app.models.experiment import Experiment


class HumanFeedbackSourceMethod(enum.StrEnum):
    INTERVIEW = "interview"
    USABILITY_TEST = "usability_test"
    SURVEY = "survey"
    OBSERVATION = "observation"
    OTHER = "other"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class HumanFeedback(Base):
    __tablename__ = "human_feedback"
    __table_args__ = (
        UniqueConstraint(
            "experiment_id",
            "participant_label",
            "variant_key",
            name="uq_human_feedback_experiment_participant_variant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False
    )
    participant_label: Mapped[str] = mapped_column(String(100), nullable=False)
    variant_key: Mapped[VariantKey] = mapped_column(
        Enum(VariantKey, native_enum=False, length=1), nullable=False
    )
    task_outcome: Mapped[TaskOutcome] = mapped_column(
        Enum(TaskOutcome, native_enum=False, length=20), nullable=False
    )
    clarity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    perceived_value_score: Mapped[int] = mapped_column(Integer, nullable=False)
    adoption_intent_score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_summary: Mapped[str] = mapped_column(Text, nullable=False)
    positive_signals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    objections: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    confusion_points: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    feature_requests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    uncertainty_notes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_method: Mapped[HumanFeedbackSourceMethod] = mapped_column(
        Enum(HumanFeedbackSourceMethod, native_enum=False, length=20), nullable=False
    )
    session_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    experiment: Mapped["Experiment"] = relationship(back_populates="human_feedback")
