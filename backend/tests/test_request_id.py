"""Request ID middleware tests."""

import uuid

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.middleware.request_id import REQUEST_ID_HEADER


def test_generates_request_id_when_absent(client: TestClient) -> None:
    settings = get_settings()
    response = client.get(f"{settings.API_PREFIX}/health")

    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert request_id is not None
    assert uuid.UUID(request_id)


def test_preserves_incoming_request_id(client: TestClient) -> None:
    settings = get_settings()
    incoming_id = "test-request-id-123"

    response = client.get(
        f"{settings.API_PREFIX}/health",
        headers={REQUEST_ID_HEADER: incoming_id},
    )

    assert response.headers.get(REQUEST_ID_HEADER) == incoming_id
