"""Evidence library routes, scoped to a project."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.evidence_item import EvidenceItem
from app.schemas.evidence import EvidenceItemCreate, EvidenceItemRead, EvidenceItemUpdate
from app.services.evidence import EvidenceService

router = APIRouter(prefix="/projects/{project_id}/evidence", tags=["evidence"])


def get_evidence_service(db: Session = Depends(get_db)) -> EvidenceService:
    return EvidenceService(db)


@router.post("", response_model=EvidenceItemRead, status_code=status.HTTP_201_CREATED)
def create_evidence_item(
    project_id: int,
    payload: EvidenceItemCreate,
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceItem:
    return service.create(project_id, payload)


@router.get("", response_model=list[EvidenceItemRead])
def list_evidence_items(
    project_id: int, service: EvidenceService = Depends(get_evidence_service)
) -> list[EvidenceItem]:
    return service.list_for_project(project_id)


@router.get("/{evidence_id}", response_model=EvidenceItemRead)
def get_evidence_item(
    project_id: int,
    evidence_id: int,
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceItem:
    return service.get(project_id, evidence_id)


@router.patch("/{evidence_id}", response_model=EvidenceItemRead)
def update_evidence_item(
    project_id: int,
    evidence_id: int,
    payload: EvidenceItemUpdate,
    service: EvidenceService = Depends(get_evidence_service),
) -> EvidenceItem:
    return service.update(project_id, evidence_id, payload)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence_item(
    project_id: int,
    evidence_id: int,
    service: EvidenceService = Depends(get_evidence_service),
) -> None:
    service.delete(project_id, evidence_id)
