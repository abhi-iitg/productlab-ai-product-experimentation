"""Alembic configuration importability tests.

Exercises the real alembic.ini + alembic/env.py wiring (settings-driven URL,
Base metadata) against an isolated temp SQLite database, without creating
any actual migration revisions.
"""

from pathlib import Path

import pytest
from alembic.command import current
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def test_alembic_script_directory_has_single_head_revision() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    heads = script.get_revisions("heads")
    assert len(heads) == 1


def test_alembic_env_runs_against_temp_sqlite(
    temp_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    get_settings.cache_clear()

    # Should not raise: env.py imports app settings/metadata, resolves the
    # DATABASE_URL from settings, connects, and reports no current revision.
    current(_alembic_config())
