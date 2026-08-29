"""create insights and decision_memos

Revision ID: 25b3d28e2ef6
Revises: c46051cccf9f
Create Date: 2026-07-30 19:50:06.397070

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "25b3d28e2ef6"
down_revision: str | Sequence[str] | None = "c46051cccf9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "STRENGTH",
                "OBJECTION",
                "CONFUSION",
                "FEATURE_REQUEST",
                "UNCERTAINTY",
                "DISAGREEMENT",
                name="insightcategory",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column(
            "variant_scope",
            sa.Enum("A", "B", "BOTH", name="variantscope", native_enum=False, length=4),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("persona_count", sa.Integer(), nullable=False),
        sa.Column("supporting_run_ids", sa.JSON(), nullable=False),
        sa.Column("supporting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column(
            "confidence_level",
            sa.Enum("LOW", "MEDIUM", "HIGH", name="confidencelevel", native_enum=False, length=10),
            nullable=False,
        ),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id",
            "title",
            "category",
            "variant_scope",
            name="uq_insight_experiment_title_category_variant",
        ),
    )
    op.create_table(
        "decision_memos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column(
            "recommendation",
            sa.Enum(
                "PROCEED",
                "ITERATE",
                "STOP",
                name="recommendation",
                native_enum=False,
                length=10,
            ),
            nullable=False,
        ),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("supporting_findings", sa.JSON(), nullable=False),
        sa.Column("weakest_assumptions", sa.JSON(), nullable=False),
        sa.Column("recommended_product_changes", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("uncertain_conclusions", sa.JSON(), nullable=False),
        sa.Column("recommended_success_metrics", sa.JSON(), nullable=False),
        sa.Column("real_user_test", sa.JSON(), nullable=False),
        sa.Column("supporting_insight_ids", sa.JSON(), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", name="uq_decision_memo_experiment_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("decision_memos")
    op.drop_table("insights")
