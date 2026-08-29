"""Persistence operations for Persona.

Repositories only perform persistence work: no HTTP exceptions, no AI
logic. Writes flush but never commit — committing (and rolling back a
whole generation batch together) is `PersonaGenerationService`'s
responsibility.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.persona import Persona


class PersonaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_batch_for_project(
        self, project_id: int, personas_data: list[dict[str, Any]]
    ) -> list[Persona]:
        personas = [Persona(project_id=project_id, **data) for data in personas_data]
        self.db.add_all(personas)
        self.db.flush()
        return personas

    def list_for_project(self, project_id: int) -> list[Persona]:
        stmt = select(Persona).where(Persona.project_id == project_id).order_by(Persona.id)
        return list(self.db.execute(stmt).scalars())

    def get_by_id(self, persona_id: int) -> Persona | None:
        return self.db.get(Persona, persona_id)

    def delete(self, persona: Persona) -> None:
        self.db.delete(persona)
        self.db.flush()
