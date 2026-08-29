"""Business logic for anonymized real-participant feedback entry (Stage 8).

Human feedback may only be *added* once an Experiment has left
`draft`/`running` and did not outright `fail` — i.e. `completed` or
`partially_completed`, the same eligibility window as deterministic
analysis. Editing and deletion are always permitted regardless of
experiment status, since manually entered research data may need
correction after the fact. `experiment_id` can never be changed — the
update schema has no such field.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.experiment import Experiment, ExperimentStatus
from app.models.human_feedback import HumanFeedback
from app.models.project import Project
from app.repositories.experiment import ExperimentRepository
from app.repositories.human_feedback import HumanFeedbackRepository
from app.repositories.project import ProjectRepository
from app.schemas.human_feedback import HumanFeedbackCreate, HumanFeedbackUpdate

_ELIGIBLE_STATUSES = {ExperimentStatus.COMPLETED, ExperimentStatus.PARTIALLY_COMPLETED}


class HumanFeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.experiments = ExperimentRepository(db)
        self.feedback = HumanFeedbackRepository(db)

    def create(
        self, project_id: int, experiment_id: int, data: HumanFeedbackCreate
    ) -> HumanFeedback:
        self._get_project_or_404(project_id)
        experiment = self._get_experiment_or_404(project_id, experiment_id)
        self._require_eligible(experiment)

        try:
            feedback = self.feedback.create_for_experiment(experiment_id, data.model_dump())
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                f"Participant {data.participant_label!r} already has feedback recorded for "
                f"variant {data.variant_key.value}."
            ) from exc

        self._commit()
        self.db.refresh(feedback)
        return feedback

    def list_for_experiment(self, project_id: int, experiment_id: int) -> list[HumanFeedback]:
        self._get_project_or_404(project_id)
        self._get_experiment_or_404(project_id, experiment_id)
        return self.feedback.list_for_experiment(experiment_id)

    def get(self, project_id: int, experiment_id: int, feedback_id: int) -> HumanFeedback:
        self._get_project_or_404(project_id)
        self._get_experiment_or_404(project_id, experiment_id)
        feedback = self.feedback.get_by_experiment_and_id(experiment_id, feedback_id)
        if feedback is None:
            raise NotFoundError(f"Human feedback {feedback_id} not found.")
        return feedback

    def update(
        self, project_id: int, experiment_id: int, feedback_id: int, data: HumanFeedbackUpdate
    ) -> HumanFeedback:
        feedback = self.get(project_id, experiment_id, feedback_id)

        try:
            self.feedback.update(feedback, data.model_dump(exclude_unset=True))
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                f"Human feedback {feedback_id} could not be updated: another feedback record "
                "already exists for that participant and variant."
            ) from exc

        self._commit()
        self.db.refresh(feedback)
        return feedback

    def delete(self, project_id: int, experiment_id: int, feedback_id: int) -> None:
        feedback = self.get(project_id, experiment_id, feedback_id)
        self.feedback.delete(feedback)
        self._commit()

    def _require_eligible(self, experiment: Experiment) -> None:
        if experiment.status not in _ELIGIBLE_STATUSES:
            raise ConflictError(
                f"Experiment {experiment.id} must be completed or partially_completed "
                "before human feedback can be added."
            )

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    def _get_experiment_or_404(self, project_id: int, experiment_id: int) -> Experiment:
        experiment = self.experiments.get_by_project_and_id(project_id, experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found.")
        return experiment

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
