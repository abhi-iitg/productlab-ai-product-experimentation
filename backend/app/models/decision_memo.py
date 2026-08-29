"""DecisionMemo domain model: the structured Proceed/Iterate/Stop memo
produced from an Experiment's persisted Insights (Stage 6).

Exactly one `DecisionMemo` may exist per `Experiment` (enforced by a unique
constraint on `experiment_id` and, defensively, at the service layer before
generation). Immutable once persisted — no editing or deletion is exposed.
`real_user_test` is a validated JSON object (see
`app.schemas.decision_memo.RealUserTestPlan`); `supporting_insight_ids` must
reference only `Insight`s belonging to the same Experiment, enforced by
Pydantic validation before persistence, never here.
"""

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.experiment import Experiment


class Recommendation(enum.StrEnum):
    PROCEED = "proceed"
    ITERATE = "iterate"
    STOP = "stop"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DecisionMemo(Base):
    __tablename__ = "decision_memos"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    recommendation: Mapped[Recommendation] = mapped_column(
        Enum(Recommendation, native_enum=False, length=10), nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_findings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    weakest_assumptions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommended_product_changes: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    risks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    uncertain_conclusions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recommended_success_metrics: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    real_user_test: Mapped[dict] = mapped_column(JSON, nullable=False)
    supporting_insight_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    experiment: Mapped["Experiment"] = relationship(back_populates="decision_memo")
