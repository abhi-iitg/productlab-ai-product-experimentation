"""Centralized exception handling tests.

Builds a throwaway FastAPI app (not the production app/router) with a
route that deliberately raises, purely to exercise
`register_exception_handlers` in isolation.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers


def _build_failing_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise ValueError("something exploded with sensitive internal detail")

    return app


def test_unhandled_exception_returns_safe_generic_response() -> None:
    app = _build_failing_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error."}


def test_unhandled_exception_does_not_leak_internal_details() -> None:
    app = _build_failing_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom")

    assert "sensitive internal detail" not in response.text
    assert "Traceback" not in response.text
