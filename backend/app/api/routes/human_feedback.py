"""Anonymized real-participant feedback and comparison routes, scoped to a
project/experiment (Stage 8).

Routes stay thin: request/response validation and delegating to
`HumanFeedbackService`/`HumanComparisonService`. No aggregation or
comparison logic lives here.

The static `/comparison` route is declared before the dynamic
`/{feedback_id}` route so it is never shadowed.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.human_feedback import HumanFeedback
from app.schemas.human_comparison import HumanComparisonResponse
from app.schemas.human_feedback import HumanFeedbackCreate, HumanFeedbackRead, HumanFeedbackUpdate
from app.services.human_comparison import HumanComparisonService
from app.services.human_feedback import HumanFeedbackService

router = APIRouter(
    prefix="/projects/{project_id}/experiments/{experiment_id}/human-feedback",
    tags=["human-feedback"],
)


def get_human_feedback_service(db: Session = Depends(get_db)) -> HumanFeedbackService:
    return HumanFeedbackService(db)


def get_human_comparison_service(db: Session = Depends(get_db)) -> HumanComparisonService:
    return HumanComparisonService(db)


@router.post("", response_model=HumanFeedbackRead, status_code=status.HTTP_201_CREATED)
def create_human_feedback(
    project_id: int,
    experiment_id: int,
    payload: HumanFeedbackCreate,
    service: HumanFeedbackService = Depends(get_human_feedback_service),
) -> HumanFeedback:
    return service.create(project_id, experiment_id, payload)


@router.get("", response_model=list[HumanFeedbackRead])
def list_human_feedback(
    project_id: int,
    experiment_id: int,
    service: HumanFeedbackService = Depends(get_human_feedback_service),
) -> list[HumanFeedback]:
    return service.list_for_experiment(project_id, experiment_id)


@router.get("/comparison", response_model=HumanComparisonResponse)
def get_human_comparison(
    project_id: int,
    experiment_id: int,
    service: HumanComparisonService = Depends(get_human_comparison_service),
) -> HumanComparisonResponse:
    return service.compare(project_id, experiment_id)


@router.get("/{feedback_id}", response_model=HumanFeedbackRead)
def get_human_feedback_item(
    project_id: int,
    experiment_id: int,
    feedback_id: int,
    service: HumanFeedbackService = Depends(get_human_feedback_service),
) -> HumanFeedback:
    return service.get(project_id, experiment_id, feedback_id)


@router.patch("/{feedback_id}", response_model=HumanFeedbackRead)
def update_human_feedback_item(
    project_id: int,
    experiment_id: int,
    feedback_id: int,
    payload: HumanFeedbackUpdate,
    service: HumanFeedbackService = Depends(get_human_feedback_service),
) -> HumanFeedback:
    return service.update(project_id, experiment_id, feedback_id, payload)


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_human_feedback_item(
    project_id: int,
    experiment_id: int,
    feedback_id: int,
    service: HumanFeedbackService = Depends(get_human_feedback_service),
) -> None:
    service.delete(project_id, experiment_id, feedback_id)
