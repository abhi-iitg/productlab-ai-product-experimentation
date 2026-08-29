"""Engine, session factory, and FastAPI session dependency.

SQLite is the only supported database for the MVP. When the configured
DATABASE_URL points at a local file (not `:memory:`), the parent directory
is created if missing so a fresh checkout can start the app without any
manual setup step.

The engine and session factory are created lazily and cached, so importing
this module has no side effects (no directories or files are created until
a session is actually requested). Tests override the `get_db` FastAPI
dependency directly rather than mutating this module's global state.
"""

from collections.abc import Generator
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def ensure_sqlite_directory_exists(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return

    path = urlsplit(database_url).path
    if not path or path == "/:memory:":
        return

    # A single leading slash is the netloc/path separator in the sqlite URL,
    # not part of the filesystem path. sqlite:///rel/path.db has one (relative),
    # sqlite:////abs/path.db has two (absolute) — strip only the separator.
    db_path = Path(path[1:] if path.startswith("/") else path)
    if db_path.parent and str(db_path.parent) not in ("", "."):
        db_path.parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(settings: Settings | None = None) -> Engine:
    settings = settings or get_settings()
    ensure_sqlite_directory_exists(settings.DATABASE_URL)

    connect_args: dict[str, object] = {}
    if settings.DATABASE_URL.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(settings.DATABASE_URL, connect_args=connect_args)


@lru_cache
def get_engine() -> Engine:
    return create_db_engine(get_settings())


@lru_cache
def get_session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def get_db() -> Generator[Session]:
    """FastAPI dependency yielding a database session per request.

    Rolls back on any exception raised while the session is in use and
    always closes the session afterwards, so a failed request never
    leaves a dangling transaction on the connection.
    """
    db = get_session_factory()()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
