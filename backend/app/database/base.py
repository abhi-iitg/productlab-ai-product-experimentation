"""SQLAlchemy declarative base.

Domain models (`app.models`) subclass `Base`. Alembic autogeneration reads
`Base.metadata` to detect schema changes.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
