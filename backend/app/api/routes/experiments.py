"""Experiment and SimulationRun routes, scoped to a project.

Routes stay thin: request/response validation and delegating to
`ExperimentService` (CRUD, read-only run access) or
`ExperimentExecutionService` (execution only). No prompt text, provider
calls, or context assembly happen here.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.llm.factory import build_simulation_provider
from app.llm.simulation_provider import SimulationLLMProvider
from app.models.experiment import Experiment
from app.models.simulation_run import SimulationRun
from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentExecuteRequest,
    ExperimentExecutionSummary,
    ExperimentRead,
    ExperimentUpdate,
)
from app.schemas.simulation_run import SimulationRunRead
from app.services.experiment import ExperimentService
from app.services.experiment_execution import ExperimentExecutionService

router = APIRouter(prefix="/projects/{project_id}/experiments", tags=["experiments"])


def get_experiment_service(db: Session = Depends(get_db)) -> ExperimentService:
    return ExperimentService(db)


def get_simulation_provider() -> SimulationLLMProvider:
    return build_simulation_provider()


def get_experiment_execution_service(
    db: Session = Depends(get_db),
    provider: SimulationLLMProvider = Depends(get_simulation_provider),
) -> ExperimentExecutionService:
    return ExperimentExecutionService(db, provider)


@router.post("", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
def create_experiment(
    project_id: int,
    payload: ExperimentCreate,
    service: ExperimentService = Depends(get_experiment_service),
) -> Experiment:
    return service.create(project_id, payload)


@router.get("", response_model=list[ExperimentRead])
def list_experiments(
    project_id: int, service: ExperimentService = Depends(get_experiment_service)
) -> list[Experiment]:
    return service.list_for_project(project_id)


@router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(
    project_id: int,
    experiment_id: int,
    service: ExperimentService = Depends(get_experiment_service),
) -> Experiment:
    return service.get(project_id, experiment_id)


@router.patch("/{experiment_id}", response_model=ExperimentRead)
def update_experiment(
    project_id: int,
    experiment_id: int,
    payload: ExperimentUpdate,
    service: ExperimentService = Depends(get_experiment_service),
) -> Experiment:
    return service.update(project_id, experiment_id, payload)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experiment(
    project_id: int,
    experiment_id: int,
    service: ExperimentService = Depends(get_experiment_service),
) -> None:
    service.delete(project_id, experiment_id)


@router.post("/{experiment_id}/execute", response_model=ExperimentExecutionSummary)
def execute_experiment(
    project_id: int,
    experiment_id: int,
    payload: ExperimentExecuteRequest,
    service: ExperimentExecutionService = Depends(get_experiment_execution_service),
) -> ExperimentExecutionSummary:
    return service.execute(project_id, experiment_id, payload)


@router.get("/{experiment_id}/runs", response_model=list[SimulationRunRead])
def list_runs(
    project_id: int,
    experiment_id: int,
    service: ExperimentService = Depends(get_experiment_service),
) -> list[SimulationRun]:
    return service.list_runs(project_id, experiment_id)


@router.get("/{experiment_id}/runs/{run_id}", response_model=SimulationRunRead)
def get_run(
    project_id: int,
    experiment_id: int,
    run_id: int,
    service: ExperimentService = Depends(get_experiment_service),
) -> SimulationRun:
    return service.get_run(project_id, experiment_id, run_id)
