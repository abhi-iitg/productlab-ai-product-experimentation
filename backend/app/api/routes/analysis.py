"""Analytics, Insight, and Decision Memo routes, scoped to a project/experiment.

Routes stay thin: request/response validation and delegating to
`ExperimentAnalyticsService`, `InsightGenerationService`, or
`DecisionMemoService`. No prompt text, provider calls, or context assembly
happen here.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.llm.decision_provider import DecisionMemoLLMProvider
from app.llm.factory import build_decision_memo_provider, build_insight_provider
from app.llm.insight_provider import InsightLLMProvider
from app.models.decision_memo import DecisionMemo
from app.models.insight import Insight
from app.schemas.analytics import AnalyticsResponse
from app.schemas.decision_memo import DecisionMemoRead
from app.schemas.insight import InsightGenerateResponse, InsightRead
from app.services.analytics import ExperimentAnalyticsService
from app.services.decision_memo import DecisionMemoService
from app.services.insight_generation import InsightGenerationService

router = APIRouter(prefix="/projects/{project_id}/experiments/{experiment_id}", tags=["analysis"])


def get_analytics_service(db: Session = Depends(get_db)) -> ExperimentAnalyticsService:
    return ExperimentAnalyticsService(db)


def get_insight_provider() -> InsightLLMProvider:
    return build_insight_provider()


def get_insight_generation_service(
    db: Session = Depends(get_db),
    provider: InsightLLMProvider = Depends(get_insight_provider),
) -> InsightGenerationService:
    return InsightGenerationService(db, provider)


def get_decision_memo_provider() -> DecisionMemoLLMProvider:
    return build_decision_memo_provider()


def get_decision_memo_service(
    db: Session = Depends(get_db),
    provider: DecisionMemoLLMProvider = Depends(get_decision_memo_provider),
) -> DecisionMemoService:
    return DecisionMemoService(db, provider)


@router.get("/analysis", response_model=AnalyticsResponse)
def get_analysis(
    project_id: int,
    experiment_id: int,
    service: ExperimentAnalyticsService = Depends(get_analytics_service),
) -> AnalyticsResponse:
    return service.analyze(project_id, experiment_id)


@router.post(
    "/insights/generate",
    response_model=InsightGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_insights(
    project_id: int,
    experiment_id: int,
    service: InsightGenerationService = Depends(get_insight_generation_service),
) -> InsightGenerateResponse:
    insights = service.generate(project_id, experiment_id)
    prompt_version = insights[0].prompt_version
    model_name = insights[0].model_name
    return InsightGenerateResponse(
        experiment_id=experiment_id,
        prompt_version=prompt_version,
        model_name=model_name,
        insight_count=len(insights),
        insights=[InsightRead.model_validate(insight) for insight in insights],
    )


@router.get("/insights", response_model=list[InsightRead])
def list_insights(
    project_id: int,
    experiment_id: int,
    service: InsightGenerationService = Depends(get_insight_generation_service),
) -> list[Insight]:
    return service.list_for_experiment(project_id, experiment_id)


@router.post(
    "/decision-memo/generate",
    response_model=DecisionMemoRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_decision_memo(
    project_id: int,
    experiment_id: int,
    service: DecisionMemoService = Depends(get_decision_memo_service),
) -> DecisionMemo:
    return service.generate(project_id, experiment_id)


@router.get("/decision-memo", response_model=DecisionMemoRead)
def get_decision_memo(
    project_id: int,
    experiment_id: int,
    service: DecisionMemoService = Depends(get_decision_memo_service),
) -> DecisionMemo:
    return service.get(project_id, experiment_id)
