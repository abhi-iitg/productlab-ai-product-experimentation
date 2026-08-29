"""SQLite engine/session creation and lifecycle tests."""

from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.database import session as db_session
from app.database.session import create_db_engine, ensure_sqlite_directory_exists


def test_create_db_engine_connects_to_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "engine_test.db"
    settings = Settings(DATABASE_URL=f"sqlite:///{db_path}", _env_file=None)

    engine = create_db_engine(settings)
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
            assert result == 1
    finally:
        engine.dispose()

    assert db_path.parent.is_dir()


def test_ensure_sqlite_directory_exists_creates_missing_parent(tmp_path: Path) -> None:
    db_path = tmp_path / "a" / "b" / "c.db"
    assert not db_path.parent.exists()

    ensure_sqlite_directory_exists(f"sqlite:///{db_path}")

    assert db_path.parent.is_dir()


def test_ensure_sqlite_directory_exists_ignores_in_memory_url() -> None:
    # Should not raise for the in-memory special case.
    ensure_sqlite_directory_exists("sqlite:///:memory:")


def _fake_get_session_factory(real_session):
    """Stand in for db_session.get_session_factory (not the factory itself).

    get_db() calls get_session_factory()() — get the factory, then call it —
    so this needs two levels: a get_session_factory replacement that returns
    a factory that returns real_session.
    """

    def factory():
        return real_session

    def fake_get_session_factory():
        return factory

    # conftest's temp_database_url fixture calls get_session_factory.cache_clear()
    # on teardown; its finalizer can run before monkeypatch reverts this
    # replacement, so the stand-in needs a harmless cache_clear of its own.
    fake_get_session_factory.cache_clear = lambda: None
    return fake_get_session_factory


def test_get_db_rolls_back_and_closes_on_exception(
    temp_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_session = db_session.get_session_factory()()
    calls: list[str] = []
    original_rollback, original_close = real_session.rollback, real_session.close

    def fake_rollback() -> None:
        calls.append("rollback")
        original_rollback()

    def fake_close() -> None:
        calls.append("close")
        original_close()

    monkeypatch.setattr(real_session, "rollback", fake_rollback)
    monkeypatch.setattr(real_session, "close", fake_close)
    monkeypatch.setattr(db_session, "get_session_factory", _fake_get_session_factory(real_session))

    gen = db_session.get_db()
    db = next(gen)
    assert db is real_session

    with pytest.raises(ValueError):
        gen.throw(ValueError("boom"))

    assert calls == ["rollback", "close"]


def test_get_db_closes_without_rollback_on_success(
    temp_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_session = db_session.get_session_factory()()
    calls: list[str] = []
    original_close = real_session.close

    def fake_close() -> None:
        calls.append("close")
        original_close()

    monkeypatch.setattr(real_session, "rollback", lambda: calls.append("rollback"))
    monkeypatch.setattr(real_session, "close", fake_close)
    monkeypatch.setattr(db_session, "get_session_factory", _fake_get_session_factory(real_session))

    gen = db_session.get_db()
    next(gen)
    with pytest.raises(StopIteration):
        next(gen)

    assert calls == ["close"]


def test_get_engine_is_cached(temp_database_url: str) -> None:
    assert db_session.get_engine() is db_session.get_engine()
