"""Business logic for the Evidence Library workflow.

Every operation is scoped to a project: evidence belonging to one project
must never be retrievable or editable through another project's ID.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.evidence_item import EvidenceItem
from app.models.project import Project
from app.repositories.evidence import EvidenceRepository
from app.repositories.project import ProjectRepository
from app.schemas.evidence import EvidenceItemCreate, EvidenceItemUpdate


class EvidenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.evidence = EvidenceRepository(db)
        self.projects = ProjectRepository(db)

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    def create(self, project_id: int, data: EvidenceItemCreate) -> EvidenceItem:
        self._get_project_or_404(project_id)
        evidence_item = self.evidence.create_for_project(project_id, data.model_dump())
        self._commit()
        self.db.refresh(evidence_item)
        return evidence_item

    def list_for_project(self, project_id: int) -> list[EvidenceItem]:
        self._get_project_or_404(project_id)
        return self.evidence.list_for_project(project_id)

    def get(self, project_id: int, evidence_id: int) -> EvidenceItem:
        self._get_project_or_404(project_id)
        evidence_item = self.evidence.get_by_id(evidence_id)
        if evidence_item is None or evidence_item.project_id != project_id:
            raise NotFoundError(f"Evidence item {evidence_id} not found.")
        return evidence_item

    def update(self, project_id: int, evidence_id: int, data: EvidenceItemUpdate) -> EvidenceItem:
        evidence_item = self.get(project_id, evidence_id)
        self.evidence.update(evidence_item, data.model_dump(exclude_unset=True))
        self._commit()
        self.db.refresh(evidence_item)
        return evidence_item

    def delete(self, project_id: int, evidence_id: int) -> None:
        evidence_item = self.get(project_id, evidence_id)
        self.evidence.delete(evidence_item)
        self._commit()

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
