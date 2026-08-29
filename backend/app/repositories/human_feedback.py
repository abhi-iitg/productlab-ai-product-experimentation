"""Persistence operations for HumanFeedback.

Repositories only perform persistence work: no HTTP exceptions, no
analytics/comparison logic. `create`/`update`/`delete` flush but never
commit — committing is a service-layer responsibility.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.human_feedback import HumanFeedback


class HumanFeedbackRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_for_experiment(self, experiment_id: int, data: dict[str, Any]) -> HumanFeedback:
        feedback = HumanFeedback(experiment_id=experiment_id, **data)
        self.db.add(feedback)
        self.db.flush()
        return feedback

    def list_for_experiment(self, experiment_id: int) -> list[HumanFeedback]:
        stmt = (
            select(HumanFeedback)
            .where(HumanFeedback.experiment_id == experiment_id)
            .order_by(HumanFeedback.session_date, HumanFeedback.created_at, HumanFeedback.id)
        )
        return list(self.db.execute(stmt).scalars())

    def get_by_experiment_and_id(
        self, experiment_id: int, feedback_id: int
    ) -> HumanFeedback | None:
        feedback = self.db.get(HumanFeedback, feedback_id)
        if feedback is None or feedback.experiment_id != experiment_id:
            return None
        return feedback

    def update(self, feedback: HumanFeedback, data: dict[str, Any]) -> HumanFeedback:
        for key, value in data.items():
            setattr(feedback, key, value)
        self.db.flush()
        return feedback

    def delete(self, feedback: HumanFeedback) -> None:
        self.db.delete(feedback)
        self.db.flush()
