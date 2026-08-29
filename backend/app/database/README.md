# database

- `base.py` — SQLAlchemy 2.x `DeclarativeBase` (`Base`). Domain models in
  `app.models` subclass it; Alembic autogeneration reads its metadata.
- `session.py` — lazily-created, cached engine and session factory, plus
  the `get_db()` FastAPI dependency (commits are the caller's
  responsibility; the dependency rolls back on exception and always closes
  the session). SQLite is the only supported database for the MVP.

`Project` and `EvidenceItem` (see `app/models/`) are the first real
domain models, with a matching Alembic migration in `alembic/versions/`.
