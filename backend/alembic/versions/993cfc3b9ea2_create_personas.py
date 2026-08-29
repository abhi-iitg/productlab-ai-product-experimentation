"""create personas

Revision ID: 993cfc3b9ea2
Revises: b6e2fd896faa
Create Date: 2026-07-30 18:32:46.860615

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "993cfc3b9ea2"
down_revision: str | Sequence[str] | None = "b6e2fd896faa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "personas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("segment_label", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("goals", sa.JSON(), nullable=False),
        sa.Column("pain_points", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("behaviors", sa.JSON(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("unsupported_assumptions", sa.JSON(), nullable=False),
        sa.Column(
            "confidence_level",
            sa.Enum("LOW", "MEDIUM", "HIGH", name="confidencelevel", native_enum=False, length=10),
            nullable=False,
        ),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("personas")
