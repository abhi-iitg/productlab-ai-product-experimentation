"""Business logic for evidence-grounded persona generation.

Owns the full Stage 4 workflow: verify the project exists, select and
verify ownership of evidence, build the deterministic context, call the LLM
provider abstraction, and persist every generated persona in a single
transaction. Provider and validation failures are translated into the safe,
generic exceptions in `app.core.exceptions` — no provider internals ever
reach the API boundary.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidRequestError,
    NotFoundError,
    ProviderConfigurationError,
    ProviderError,
)
from app.llm.context import PersonaContextTooLargeError, build_persona_context
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMEmptyOutputError,
    LLMInvalidOutputError,
    LLMProviderError,
    LLMRateLimitError,
    LLMStatusError,
    LLMTimeoutError,
)
from app.llm.prompts import PERSONA_PROMPT_VERSION
from app.llm.provider import PersonaLLMProvider
from app.models.evidence_item import EvidenceItem
from app.models.persona import Persona
from app.models.project import Project
from app.repositories.evidence import EvidenceRepository
from app.repositories.persona import PersonaRepository
from app.repositories.project import ProjectRepository
from app.schemas.persona import PersonaGenerateRequest


class PersonaGenerationService:
    def __init__(self, db: Session, provider: PersonaLLMProvider) -> None:
        self.db = db
        self.provider = provider
        self.projects = ProjectRepository(db)
        self.evidence = EvidenceRepository(db)
        self.personas = PersonaRepository(db)

    def generate(self, project_id: int, request: PersonaGenerateRequest) -> list[Persona]:
        project = self._get_project_or_404(project_id)
        evidence_items = self._select_evidence(project_id, request.selected_evidence_ids)
        allowed_evidence_ids = {item.id for item in evidence_items}

        try:
            context = build_persona_context(project, evidence_items)
        except PersonaContextTooLargeError as exc:
            raise InvalidRequestError(str(exc)) from exc

        try:
            result = self.provider.generate_personas(
                persona_count=request.persona_count,
                context=context,
                focus=request.focus,
                allowed_evidence_ids=allowed_evidence_ids,
            )
        except LLMConfigurationError as exc:
            raise ProviderConfigurationError("The AI provider is not configured.") from exc
        except (
            LLMTimeoutError,
            LLMRateLimitError,
            LLMStatusError,
            LLMEmptyOutputError,
            LLMInvalidOutputError,
            LLMProviderError,
        ) as exc:
            raise ProviderError("The AI provider was unable to generate personas.") from exc

        personas_data = [
            {
                "name": persona.name,
                "segment_label": persona.segment_label,
                "summary": persona.summary,
                "goals": persona.goals,
                "pain_points": persona.pain_points,
                "constraints": persona.constraints,
                "behaviors": persona.behaviors,
                "evidence_references": [ref.model_dump() for ref in persona.evidence_references],
                "unsupported_assumptions": persona.unsupported_assumptions,
                "confidence_level": persona.confidence_level,
                "prompt_version": PERSONA_PROMPT_VERSION,
                "model_name": self.provider.model_name,
            }
            for persona in result.personas
        ]

        personas = self.personas.create_batch_for_project(project_id, personas_data)
        self._commit()
        for persona in personas:
            self.db.refresh(persona)
        return personas

    def list_for_project(self, project_id: int) -> list[Persona]:
        self._get_project_or_404(project_id)
        return self.personas.list_for_project(project_id)

    def get(self, project_id: int, persona_id: int) -> Persona:
        self._get_project_or_404(project_id)
        persona = self.personas.get_by_id(persona_id)
        if persona is None or persona.project_id != project_id:
            raise NotFoundError(f"Persona {persona_id} not found.")
        return persona

    def delete(self, project_id: int, persona_id: int) -> None:
        persona = self.get(project_id, persona_id)
        self.personas.delete(persona)
        self._commit()

    def _get_project_or_404(self, project_id: int) -> Project:
        project = self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found.")
        return project

    def _select_evidence(
        self, project_id: int, selected_ids: list[int] | None
    ) -> list[EvidenceItem]:
        all_evidence = self.evidence.list_for_project(project_id)

        if selected_ids is None:
            evidence_items = all_evidence
        else:
            by_id = {item.id: item for item in all_evidence}
            missing = [evidence_id for evidence_id in selected_ids if evidence_id not in by_id]
            if missing:
                raise InvalidRequestError(
                    f"Evidence item(s) {missing} do not belong to project {project_id}."
                )
            evidence_items = sorted(
                (by_id[evidence_id] for evidence_id in selected_ids), key=lambda item: item.id
            )

        if not evidence_items:
            raise InvalidRequestError(
                f"Project {project_id} has no usable evidence for persona generation."
            )
        return evidence_items

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
