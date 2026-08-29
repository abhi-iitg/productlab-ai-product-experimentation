"""Persona routes, scoped to a project.

Routes stay thin: request/response validation and delegating to
`PersonaGenerationService`. No prompt text, provider calls, or context
assembly happen here.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.llm.factory import build_persona_provider
from app.llm.prompts import PERSONA_PROMPT_VERSION
from app.llm.provider import PersonaLLMProvider
from app.models.persona import Persona
from app.schemas.persona import PersonaGenerateRequest, PersonaGenerateResponse, PersonaRead
from app.services.persona import PersonaGenerationService

router = APIRouter(prefix="/projects/{project_id}/personas", tags=["personas"])


def get_persona_provider() -> PersonaLLMProvider:
    return build_persona_provider()


def get_persona_service(
    db: Session = Depends(get_db),
    provider: PersonaLLMProvider = Depends(get_persona_provider),
) -> PersonaGenerationService:
    return PersonaGenerationService(db, provider)


@router.post(
    "/generate", response_model=PersonaGenerateResponse, status_code=status.HTTP_201_CREATED
)
def generate_personas(
    project_id: int,
    payload: PersonaGenerateRequest,
    service: PersonaGenerationService = Depends(get_persona_service),
) -> PersonaGenerateResponse:
    personas = service.generate(project_id, payload)
    return PersonaGenerateResponse(
        project_id=project_id,
        prompt_version=PERSONA_PROMPT_VERSION,
        model_name=service.provider.model_name,
        persona_count=len(personas),
        personas=[PersonaRead.model_validate(persona) for persona in personas],
    )


@router.get("", response_model=list[PersonaRead])
def list_personas(
    project_id: int, service: PersonaGenerationService = Depends(get_persona_service)
) -> list[Persona]:
    return service.list_for_project(project_id)


@router.get("/{persona_id}", response_model=PersonaRead)
def get_persona(
    project_id: int,
    persona_id: int,
    service: PersonaGenerationService = Depends(get_persona_service),
) -> Persona:
    return service.get(project_id, persona_id)


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_persona(
    project_id: int,
    persona_id: int,
    service: PersonaGenerationService = Depends(get_persona_service),
) -> None:
    service.delete(project_id, persona_id)
