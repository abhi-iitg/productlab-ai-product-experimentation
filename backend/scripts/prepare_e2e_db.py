"""Prepare an isolated, freshly migrated SQLite database for Playwright E2E runs.

Deletes any existing file at the E2E database path (deterministic cleanup
before the suite, so no run is affected by a previous run's leftover data),
then runs `alembic upgrade head` against it. Never touches the developer's
own `data/app.db` — refuses to run unless `APP_ENV=test` and `DATABASE_URL`
is a sqlite URL whose path contains "e2e", as a safety check against
accidentally wiping a real database.

Invoked by the Playwright backend `webServer` command
(`frontend/playwright.config.ts`) before `uvicorn` starts, and can also be
run directly:

    cd backend
    APP_ENV=test DATABASE_URL=sqlite:///./data/e2e-test.db \\
        python scripts/prepare_e2e_db.py
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _sqlite_path_from_url(database_url: str) -> Path:
    raw_path = urlsplit(database_url).path
    relative = raw_path[1:] if raw_path.startswith("/") else raw_path
    return (BACKEND_DIR / relative).resolve()


def main() -> None:
    app_env = os.environ.get("APP_ENV")
    database_url = os.environ.get("DATABASE_URL", "")

    if app_env != "test":
        print(
            f"Refusing to prepare the E2E database: APP_ENV must be 'test' (got {app_env!r}).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if not database_url.startswith("sqlite"):
        print(
            "Refusing to prepare the E2E database: DATABASE_URL must be a sqlite URL "
            f"(got {database_url!r}).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if "e2e" not in database_url:
        print(
            "Refusing to prepare the E2E database: DATABASE_URL does not look like a "
            f"dedicated E2E database file ({database_url!r}). Expected the path to "
            "contain 'e2e', as a safety check against wiping a real database.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    db_path = _sqlite_path_from_url(database_url)
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing E2E database at {db_path}")

    db_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )
    print(f"E2E database ready at {db_path}")


if __name__ == "__main__":
    main()
