"""Application factory tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_create_app_returns_fastapi_instance(temp_database_url: str) -> None:
    app = create_app()
    assert isinstance(app, FastAPI)


def test_health_is_mounted_under_configured_api_prefix(client: TestClient) -> None:
    settings = get_settings()
    response = client.get(f"{settings.API_PREFIX}/health")
    assert response.status_code == 200


def test_health_is_not_mounted_at_bare_path(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 404
