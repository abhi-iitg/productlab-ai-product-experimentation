"""Top-level API router. Route modules are registered here as they're added."""

from fastapi import APIRouter

from app.api.routes import (
    analysis,
    evidence,
    experiments,
    health,
    human_feedback,
    personas,
    projects,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(projects.router)
api_router.include_router(evidence.router)
api_router.include_router(personas.router)
api_router.include_router(experiments.router)
api_router.include_router(analysis.router)
api_router.include_router(human_feedback.router)
