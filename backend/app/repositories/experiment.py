"""Persistence operations for Experiment and Variant.

Repositories only perform persistence work: no HTTP exceptions, no
provider/AI logic, no cross-entity business validation. Writes flush but
never commit — committing is `ExperimentService`'s and
`ExperimentExecutionService`'s responsibility.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.experiment import Experiment, ExperimentStatus, experiment_personas
from app.models.persona import Persona
from app.models.variant import Variant


class ExperimentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_with_variants_and_personas(
        self,
        *,
        project_id: int,
        data: dict[str, Any],
        variants: list[dict[str, Any]],
        personas: list[Persona],
    ) -> Experiment:
        experiment = Experiment(
            project_id=project_id,
            **data,
            variants=[Variant(**variant_data) for variant_data in variants],
            personas=personas,
        )
        self.db.add(experiment)
        self.db.flush()
        return experiment

    def list_for_project(self, project_id: int) -> list[Experiment]:
        stmt = select(Experiment).where(Experiment.project_id == project_id).order_by(Experiment.id)
        return list(self.db.execute(stmt).scalars())

    def get_by_project_and_id(self, project_id: int, experiment_id: int) -> Experiment | None:
        experiment = self.db.get(Experiment, experiment_id)
        if experiment is None or experiment.project_id != project_id:
            return None
        return experiment

    def get_persona_ids(self, experiment_id: int) -> list[int]:
        """Read the raw selected persona IDs directly from the association table.

        Distinct from `experiment.personas` (an inner-joined relationship,
        which silently omits IDs whose Persona row no longer exists): this
        is used at execution time specifically to detect a persona that was
        selected but has since been deleted.
        """
        stmt = (
            select(experiment_personas.c.persona_id)
            .where(experiment_personas.c.experiment_id == experiment_id)
            .order_by(experiment_personas.c.persona_id)
        )
        return list(self.db.execute(stmt).scalars())

    def update(
        self,
        experiment: Experiment,
        data: dict[str, Any],
        *,
        personas: list[Persona] | None = None,
        variants_data: list[dict[str, Any]] | None = None,
    ) -> Experiment:
        for key, value in data.items():
            setattr(experiment, key, value)

        if personas is not None:
            experiment.personas = personas

        if variants_data is not None:
            variants_by_key = {variant.key: variant for variant in experiment.variants}
            for variant_data in variants_data:
                variant = variants_by_key[variant_data["key"]]
                variant.name = variant_data["name"]
                variant.description = variant_data["description"]

        self.db.flush()
        return experiment

    def update_status(
        self,
        experiment: Experiment,
        status: ExperimentStatus,
        **timestamp_fields: Any,
    ) -> Experiment:
        experiment.status = status
        for key, value in timestamp_fields.items():
            setattr(experiment, key, value)
        self.db.flush()
        return experiment

    def delete(self, experiment: Experiment) -> None:
        self.db.delete(experiment)
        self.db.flush()
