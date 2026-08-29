"""Health endpoint tests."""

from fastapi.testclient import TestClient

from app.api.routes.health import HealthResponse
from app.core.config import get_settings


def test_health_returns_ok(client: TestClient) -> None:
    settings = get_settings()
    response = client.get(f"{settings.API_PREFIX}/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == settings.APP_NAME
    assert body["environment"] == settings.APP_ENV
    assert body["version"] == settings.APP_VERSION


def test_health_response_matches_schema(client: TestClient) -> None:
    settings = get_settings()
    response = client.get(f"{settings.API_PREFIX}/health")

    validated = HealthResponse.model_validate(response.json())
    assert validated.status == "ok"
