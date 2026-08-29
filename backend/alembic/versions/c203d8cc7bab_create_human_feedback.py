"""create human feedback

Revision ID: c203d8cc7bab
Revises: 25b3d28e2ef6
Create Date: 2026-07-31 00:22:36.499484

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c203d8cc7bab"
down_revision: str | Sequence[str] | None = "25b3d28e2ef6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "human_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("participant_label", sa.String(length=100), nullable=False),
        sa.Column(
            "variant_key",
            sa.Enum("A", "B", name="variantkey", native_enum=False, length=1),
            nullable=False,
        ),
        sa.Column(
            "task_outcome",
            sa.Enum(
                "COMPLETED",
                "PARTIALLY_COMPLETED",
                "FAILED",
                "UNCERTAIN",
                name="taskoutcome",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("clarity_score", sa.Integer(), nullable=False),
        sa.Column("perceived_value_score", sa.Integer(), nullable=False),
        sa.Column("adoption_intent_score", sa.Integer(), nullable=False),
        sa.Column("feedback_summary", sa.Text(), nullable=False),
        sa.Column("positive_signals", sa.JSON(), nullable=False),
        sa.Column("objections", sa.JSON(), nullable=False),
        sa.Column("confusion_points", sa.JSON(), nullable=False),
        sa.Column("feature_requests", sa.JSON(), nullable=False),
        sa.Column("uncertainty_notes", sa.JSON(), nullable=False),
        sa.Column(
            "source_method",
            sa.Enum(
                "INTERVIEW",
                "USABILITY_TEST",
                "SURVEY",
                "OBSERVATION",
                "OTHER",
                name="humanfeedbacksourcemethod",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("session_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id",
            "participant_label",
            "variant_key",
            name="uq_human_feedback_experiment_participant_variant",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("human_feedback")
