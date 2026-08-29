"""Business logic for the Product Brief (Project) workflow."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)

    def create(self, data: ProjectCreate) -> Project:
        project = self.projects.create(data.model_dump())
        self._commit()
        self.db.refresh(project)
        return project

    def list(self) -> list[Project]:
        return self.projects.list()

    def get(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    def update(self, project_id: int, data: ProjectUpdate) -> Project:
        project = self.get(project_id)
        self.projects.update(project, data.model_dump(exclude_unset=True))
        self._commit()
        self.db.refresh(project)
        return project

    def delete(self, project_id: int) -> None:
        project = self.get(project_id)
        self.projects.delete(project)
        self._commit()

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
