"""create experiments, variants, experiment_personas, and simulation_runs

Revision ID: c46051cccf9f
Revises: 993cfc3b9ea2
Create Date: 2026-07-30 19:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c46051cccf9f"
down_revision: str | Sequence[str] | None = "993cfc3b9ea2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("evaluation_criteria", sa.JSON(), nullable=False),
        sa.Column("repeat_count", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "RUNNING",
                "COMPLETED",
                "PARTIALLY_COMPLETED",
                "FAILED",
                name="experimentstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column(
            "key", sa.Enum("A", "B", name="variantkey", native_enum=False, length=1), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", "key", name="uq_variant_experiment_key"),
    )
    op.create_table(
        "experiment_personas",
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("persona_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("experiment_id", "persona_id"),
    )
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=False),
        sa.Column("persona_id", sa.Integer(), nullable=False),
        sa.Column("repetition_index", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "COMPLETED", "FAILED", name="simulationrunstatus", native_enum=False, length=10
            ),
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
            nullable=True,
        ),
        sa.Column("clarity_score", sa.Integer(), nullable=True),
        sa.Column("perceived_value_score", sa.Integer(), nullable=True),
        sa.Column("adoption_intent_score", sa.Integer(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("positive_signals", sa.JSON(), nullable=False),
        sa.Column("objections", sa.JSON(), nullable=False),
        sa.Column("confusion_points", sa.JSON(), nullable=False),
        sa.Column("feature_requests", sa.JSON(), nullable=False),
        sa.Column("uncertainty_notes", sa.JSON(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column(
            "failure_type",
            sa.Enum(
                "CONFIGURATION_ERROR",
                "CONTEXT_LIMIT",
                "TIMEOUT",
                "RATE_LIMIT",
                "PROVIDER_ERROR",
                "EMPTY_OUTPUT",
                "MALFORMED_JSON",
                "INVALID_SCHEMA",
                "INVALID_EVIDENCE_REFERENCE",
                "UNEXPECTED_ERROR",
                name="failuretype",
                native_enum=False,
                length=30,
            ),
            nullable=True,
        ),
        sa.Column("failure_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["variant_id"], ["variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "experiment_id",
            "variant_id",
            "persona_id",
            "repetition_index",
            name="uq_simulation_run_matrix",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("simulation_runs")
    op.drop_table("experiment_personas")
    op.drop_table("variants")
    op.drop_table("experiments")
