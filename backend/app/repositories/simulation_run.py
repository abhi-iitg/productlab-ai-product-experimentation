"""Persistence operations for SimulationRun.

Repositories only perform persistence work: no HTTP exceptions, no
provider/AI logic. `create_completed`/`create_failed` flush but never
commit — `ExperimentExecutionService` commits each run independently so
completed and failed runs remain inspectable even after a later run fails.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.simulation_run import SimulationRun, SimulationRunStatus


class SimulationRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_completed(
        self,
        *,
        experiment_id: int,
        variant_id: int,
        persona_id: int,
        repetition_index: int,
        data: dict[str, Any],
    ) -> SimulationRun:
        run = SimulationRun(
            experiment_id=experiment_id,
            variant_id=variant_id,
            persona_id=persona_id,
            repetition_index=repetition_index,
            status=SimulationRunStatus.COMPLETED,
            **data,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def create_failed(
        self,
        *,
        experiment_id: int,
        variant_id: int,
        persona_id: int,
        repetition_index: int,
        data: dict[str, Any],
    ) -> SimulationRun:
        run = SimulationRun(
            experiment_id=experiment_id,
            variant_id=variant_id,
            persona_id=persona_id,
            repetition_index=repetition_index,
            status=SimulationRunStatus.FAILED,
            **data,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def list_for_experiment(self, experiment_id: int) -> list[SimulationRun]:
        stmt = (
            select(SimulationRun)
            .where(SimulationRun.experiment_id == experiment_id)
            .order_by(SimulationRun.id)
        )
        return list(self.db.execute(stmt).scalars())

    def get_by_experiment_and_id(self, experiment_id: int, run_id: int) -> SimulationRun | None:
        run = self.db.get(SimulationRun, run_id)
        if run is None or run.experiment_id != experiment_id:
            return None
        return run
