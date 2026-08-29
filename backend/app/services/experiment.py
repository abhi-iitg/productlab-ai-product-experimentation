"""Business logic for the Experiment/Variant CRUD workflow (Stage 5).

Execution (dispatching simulation runs) is a separate concern owned by
`ExperimentExecutionService` — this service only creates, reads, updates,
and deletes experiments while they remain in `draft` status, and exposes
read-only access to persisted `SimulationRun`s.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InvalidRequestError, NotFoundError
from app.models.experiment import Experiment, ExperimentStatus
from app.models.persona import Persona
from app.models.project import Project
from app.models.simulation_run import SimulationRun
from app.repositories.experiment import ExperimentRepository
from app.repositories.persona import PersonaRepository
from app.repositories.project import ProjectRepository
from app.repositories.simulation_run import SimulationRunRepository
from app.schemas.experiment import ExperimentCreate, ExperimentUpdate

# Deterministic maximum simulation-run matrix size: selected personas x 2
# variants x repeat_count. Enforced at both creation and execution time;
# creation/execution is rejected outright rather than silently reducing
# personas or repeat count.
MAX_SIMULATION_RUNS = 30

_VARIANT_COUNT = 2


class ExperimentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.personas = PersonaRepository(db)
        self.experiments = ExperimentRepository(db)
        self.runs = SimulationRunRepository(db)

    def create(self, project_id: int, request: ExperimentCreate) -> Experiment:
        self._get_project_or_404(project_id)
        personas = self._validate_personas(project_id, request.persona_ids)
        self._validate_run_count(len(personas), request.repeat_count)

        data = request.model_dump(exclude={"persona_ids", "variants"})
        variants = [variant.model_dump() for variant in request.variants]

        experiment = self.experiments.create_with_variants_and_personas(
            project_id=project_id, data=data, variants=variants, personas=personas
        )
        self._commit()
        self.db.refresh(experiment)
        return experiment

    def list_for_project(self, project_id: int) -> list[Experiment]:
        self._get_project_or_404(project_id)
        return self.experiments.list_for_project(project_id)

    def get(self, project_id: int, experiment_id: int) -> Experiment:
        self._get_project_or_404(project_id)
        experiment = self.experiments.get_by_project_and_id(project_id, experiment_id)
        if experiment is None:
            raise NotFoundError(f"Experiment {experiment_id} not found.")
        return experiment

    def update(self, project_id: int, experiment_id: int, request: ExperimentUpdate) -> Experiment:
        experiment = self.get(project_id, experiment_id)
        self._require_draft(experiment)

        update_fields = request.model_dump(exclude_unset=True, exclude={"persona_ids", "variants"})

        personas: list[Persona] | None = None
        if request.persona_ids is not None:
            personas = self._validate_personas(project_id, request.persona_ids)

        variants_data: list[dict] | None = None
        if request.variants is not None:
            variants_data = [variant.model_dump() for variant in request.variants]

        resulting_persona_count = (
            len(personas) if personas is not None else len(experiment.personas)
        )
        resulting_repeat_count = update_fields.get("repeat_count", experiment.repeat_count)
        self._validate_run_count(resulting_persona_count, resulting_repeat_count)

        self.experiments.update(
            experiment, update_fields, personas=personas, variants_data=variants_data
        )
        self._commit()
        self.db.refresh(experiment)
        return experiment

    def delete(self, project_id: int, experiment_id: int) -> None:
        experiment = self.get(project_id, experiment_id)
        self._require_draft(experiment)
        self.experiments.delete(experiment)
        self._commit()

    def list_runs(self, project_id: int, experiment_id: int) -> list[SimulationRun]:
        self.get(project_id, experiment_id)
        return self.runs.list_for_experiment(experiment_id)

    def get_run(self, project_id: int, experiment_id: int, run_id: int) -> SimulationRun:
        self.get(project_id, experiment_id)
        run = self.runs.get_by_experiment_and_id(experiment_id, run_id)
        if run is None:
            raise NotFoundError(f"Simulation run {run_id} not found.")
        return run

    def _require_draft(self, experiment: Experiment) -> None:
        if experiment.status != ExperimentStatus.DRAFT:
            raise ConflictError(
                f"Experiment {experiment.id} can only be edited or deleted while in draft status."
            )

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    def _validate_personas(self, project_id: int, persona_ids: list[int]) -> list[Persona]:
        project_personas = self.personas.list_for_project(project_id)
        all_personas = {persona.id: persona for persona in project_personas}
        missing = [persona_id for persona_id in persona_ids if persona_id not in all_personas]
        if missing:
            raise InvalidRequestError(
                f"Persona(s) {missing} do not belong to project {project_id}."
            )
        return [all_personas[persona_id] for persona_id in persona_ids]

    def _validate_run_count(self, persona_count: int, repeat_count: int) -> None:
        total_runs = persona_count * _VARIANT_COUNT * repeat_count
        if total_runs > MAX_SIMULATION_RUNS:
            raise InvalidRequestError(
                f"Calculated {total_runs} simulation runs (personas x 2 variants x "
                f"repeat_count) exceeds the maximum of {MAX_SIMULATION_RUNS}."
            )

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
