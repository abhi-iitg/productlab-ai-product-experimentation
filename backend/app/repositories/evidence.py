"""Persistence operations for EvidenceItem.

Repositories only perform persistence work: no HTTP exceptions, no AI
logic. `create`/`update`/`delete` flush but never commit — committing is a
service-layer responsibility.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence_item import EvidenceItem


class EvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_for_project(self, project_id: int, data: dict[str, Any]) -> EvidenceItem:
        evidence_item = EvidenceItem(project_id=project_id, **data)
        self.db.add(evidence_item)
        self.db.flush()
        return evidence_item

    def list_for_project(self, project_id: int) -> list[EvidenceItem]:
        stmt = (
            select(EvidenceItem)
            .where(EvidenceItem.project_id == project_id)
            .order_by(EvidenceItem.id)
        )
        return list(self.db.execute(stmt).scalars())

    def get_by_id(self, evidence_id: int) -> EvidenceItem | None:
        return self.db.get(EvidenceItem, evidence_id)

    def update(self, evidence_item: EvidenceItem, data: dict[str, Any]) -> EvidenceItem:
        for key, value in data.items():
            setattr(evidence_item, key, value)
        self.db.flush()
        return evidence_item

    def delete(self, evidence_item: EvidenceItem) -> None:
        self.db.delete(evidence_item)
        self.db.flush()
