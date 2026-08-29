"""Persistence operations for DecisionMemo.

Repositories only perform persistence work: no HTTP exceptions, no
provider/AI logic. `create_for_experiment` flushes but never commits —
`DecisionMemoService` owns the commit.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.decision_memo import DecisionMemo


class DecisionMemoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_for_experiment(self, experiment_id: int, data: dict[str, Any]) -> DecisionMemo:
        memo = DecisionMemo(experiment_id=experiment_id, **data)
        self.db.add(memo)
        self.db.flush()
        return memo

    def get_for_experiment(self, experiment_id: int) -> DecisionMemo | None:
        stmt = select(DecisionMemo).where(DecisionMemo.experiment_id == experiment_id)
        return self.db.execute(stmt).scalars().first()
