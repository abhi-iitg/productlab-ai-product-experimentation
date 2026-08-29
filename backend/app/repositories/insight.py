"""Persistence operations for Insight.

Repositories only perform persistence work: no HTTP exceptions, no
provider/AI logic. `create_batch_for_experiment` flushes but never commits —
`InsightGenerationService` persists the entire generated batch atomically.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.insight import Insight


class InsightRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_batch_for_experiment(
        self, experiment_id: int, insights_data: list[dict[str, Any]]
    ) -> list[Insight]:
        insights = [Insight(experiment_id=experiment_id, **data) for data in insights_data]
        self.db.add_all(insights)
        self.db.flush()
        return insights

    def list_for_experiment(self, experiment_id: int) -> list[Insight]:
        stmt = select(Insight).where(Insight.experiment_id == experiment_id).order_by(Insight.id)
        return list(self.db.execute(stmt).scalars())

    def exists_for_experiment(self, experiment_id: int) -> bool:
        stmt = select(Insight.id).where(Insight.experiment_id == experiment_id).limit(1)
        return self.db.execute(stmt).first() is not None
