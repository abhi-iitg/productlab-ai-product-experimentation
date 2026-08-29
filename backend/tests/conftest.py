"""Shared pytest fixtures.

All tests use an isolated temporary SQLite database (never a developer's
local database) and make no network calls.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers model tables on Base.metadata)
from app.core.config import get_settings
from app.database import session as database_session
from app.database.base import Base


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Ensure env-var overrides in one test never leak into the next."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def temp_database_url(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Point DATABASE_URL at an isolated temp-directory SQLite file."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    database_session.get_engine.cache_clear()
    database_session.get_session_factory.cache_clear()

    yield database_url

    # Dispose before clearing the cache so pooled sqlite connections are
    # actually closed, not just left open until garbage collection.
    if database_session.get_engine.cache_info().currsize:
        database_session.get_engine().dispose()
    database_session.get_engine.cache_clear()
    database_session.get_session_factory.cache_clear()


@pytest.fixture
def db_session(temp_database_url: str) -> Iterator[Session]:
    """A session against an isolated temp SQLite database with tables created."""
    engine = database_session.get_engine()
    Base.metadata.create_all(bind=engine)
    session = database_session.get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(temp_database_url: str) -> Iterator[TestClient]:
    from app.main import create_app

    Base.metadata.create_all(bind=database_session.get_engine())

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
