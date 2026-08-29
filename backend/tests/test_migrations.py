"""Alembic upgrade/downgrade migration behavior.

Runs the real migration(s) against an isolated temp SQLite database (never
a developer's local database).
"""

from pathlib import Path

from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Stage 3 revision (projects + evidence_items only, no personas table yet).
_STAGE_3_REVISION = "b6e2fd896faa"
# Stage 4 revision (personas table added, no experiment tables yet).
_STAGE_4_REVISION = "993cfc3b9ea2"
# Stage 5 revision (experiments/variants/simulation_runs added, no
# insights/decision_memos tables yet).
_STAGE_5_REVISION = "c46051cccf9f"
# Stage 6 revision (insights/decision_memos added, no human_feedback table yet).
_STAGE_6_REVISION = "25b3d28e2ef6"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _table_names(database_url: str) -> set[str]:
    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


_STAGE_5_TABLES = {"experiments", "variants", "experiment_personas", "simulation_runs"}
_STAGE_6_TABLES = {"insights", "decision_memos"}
_STAGE_8_TABLES = {"human_feedback"}


def test_fresh_database_upgrade_to_head_creates_domain_tables(temp_database_url: str) -> None:
    """A brand-new (base) database upgrades cleanly to head."""
    upgrade(_alembic_config(), "head")

    tables = _table_names(temp_database_url)
    assert "projects" in tables
    assert "evidence_items" in tables
    assert "personas" in tables
    assert _STAGE_5_TABLES <= tables
    assert _STAGE_6_TABLES <= tables
    assert _STAGE_8_TABLES <= tables


def test_downgrade_to_base_drops_domain_tables(temp_database_url: str) -> None:
    upgrade(_alembic_config(), "head")
    downgrade(_alembic_config(), "base")

    tables = _table_names(temp_database_url)
    assert "projects" not in tables
    assert "evidence_items" not in tables
    assert "personas" not in tables
    assert not (_STAGE_5_TABLES & tables)
    assert not (_STAGE_6_TABLES & tables)
    assert not (_STAGE_8_TABLES & tables)


def test_upgrade_downgrade_upgrade_cycle_is_repeatable(temp_database_url: str) -> None:
    config = _alembic_config()

    upgrade(config, "head")
    downgrade(config, "base")
    upgrade(config, "head")

    tables = _table_names(temp_database_url)
    assert "projects" in tables
    assert "evidence_items" in tables
    assert "personas" in tables
    assert _STAGE_5_TABLES <= tables
    assert _STAGE_6_TABLES <= tables
    assert _STAGE_8_TABLES <= tables


def test_upgrade_from_stage_4_revision_to_head_adds_experiment_tables(
    temp_database_url: str,
) -> None:
    """Simulates an existing Stage 4 database being upgraded to Stage 5."""
    config = _alembic_config()
    upgrade(config, _STAGE_4_REVISION)
    tables_before = _table_names(temp_database_url)
    assert not (_STAGE_5_TABLES & tables_before)

    upgrade(config, "head")

    tables_after = _table_names(temp_database_url)
    assert "personas" in tables_after
    assert _STAGE_5_TABLES <= tables_after


def test_downgrade_from_head_to_stage_4_revision_drops_only_experiment_tables(
    temp_database_url: str,
) -> None:
    config = _alembic_config()
    upgrade(config, "head")

    downgrade(config, _STAGE_4_REVISION)

    tables = _table_names(temp_database_url)
    assert "projects" in tables
    assert "evidence_items" in tables
    assert "personas" in tables
    assert not (_STAGE_5_TABLES & tables)


def test_variant_unique_constraint_declared_on_experiment_id_and_key(
    temp_database_url: str,
) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        constraints = inspect(engine).get_unique_constraints("variants")
    finally:
        engine.dispose()

    assert any(set(c["column_names"]) == {"experiment_id", "key"} for c in constraints)


def test_simulation_run_matrix_unique_constraint_declared(temp_database_url: str) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        constraints = inspect(engine).get_unique_constraints("simulation_runs")
    finally:
        engine.dispose()

    expected_columns = {"experiment_id", "variant_id", "persona_id", "repetition_index"}
    assert any(set(c["column_names"]) == expected_columns for c in constraints)


def test_experiment_foreign_keys_declare_cascade_delete(temp_database_url: str) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        inspector = inspect(engine)
        experiment_fks = inspector.get_foreign_keys("experiments")
        variant_fks = inspector.get_foreign_keys("variants")
        run_fks = inspector.get_foreign_keys("simulation_runs")
    finally:
        engine.dispose()

    assert experiment_fks[0]["options"].get("ondelete") == "CASCADE"
    assert variant_fks[0]["options"].get("ondelete") == "CASCADE"
    run_fk_by_column = {fk["constrained_columns"][0]: fk for fk in run_fks}
    assert run_fk_by_column["experiment_id"]["options"].get("ondelete") == "CASCADE"
    assert run_fk_by_column["variant_id"]["options"].get("ondelete") == "CASCADE"


def test_upgrade_from_stage_3_revision_to_head_adds_personas_table(
    temp_database_url: str,
) -> None:
    """Simulates an existing Stage 3 database being upgraded to Stage 4."""
    config = _alembic_config()
    upgrade(config, _STAGE_3_REVISION)
    tables_before = _table_names(temp_database_url)
    assert "personas" not in tables_before

    upgrade(config, "head")

    tables_after = _table_names(temp_database_url)
    assert "projects" in tables_after
    assert "evidence_items" in tables_after
    assert "personas" in tables_after


def test_downgrade_from_head_to_stage_3_revision_drops_only_personas(
    temp_database_url: str,
) -> None:
    config = _alembic_config()
    upgrade(config, "head")

    downgrade(config, _STAGE_3_REVISION)

    tables = _table_names(temp_database_url)
    assert "projects" in tables
    assert "evidence_items" in tables
    assert "personas" not in tables


def test_upgrade_from_stage_5_revision_to_head_adds_insight_and_memo_tables(
    temp_database_url: str,
) -> None:
    """Simulates an existing Stage 5 database being upgraded to Stage 6."""
    config = _alembic_config()
    upgrade(config, _STAGE_5_REVISION)
    tables_before = _table_names(temp_database_url)
    assert not (_STAGE_6_TABLES & tables_before)
    assert _STAGE_5_TABLES <= tables_before

    upgrade(config, "head")

    tables_after = _table_names(temp_database_url)
    assert _STAGE_5_TABLES <= tables_after
    assert _STAGE_6_TABLES <= tables_after


def test_downgrade_from_head_to_stage_5_revision_drops_only_stage_6_tables(
    temp_database_url: str,
) -> None:
    config = _alembic_config()
    upgrade(config, "head")

    downgrade(config, _STAGE_5_REVISION)

    tables = _table_names(temp_database_url)
    assert _STAGE_5_TABLES <= tables
    assert not (_STAGE_6_TABLES & tables)


def test_decision_memo_experiment_id_unique_constraint_declared(temp_database_url: str) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        constraints = inspect(engine).get_unique_constraints("decision_memos")
    finally:
        engine.dispose()

    assert any(c["column_names"] == ["experiment_id"] for c in constraints)


def test_insight_experiment_title_category_variant_unique_constraint_declared(
    temp_database_url: str,
) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        constraints = inspect(engine).get_unique_constraints("insights")
    finally:
        engine.dispose()

    expected_columns = {"experiment_id", "title", "category", "variant_scope"}
    assert any(set(c["column_names"]) == expected_columns for c in constraints)


def test_insight_and_decision_memo_foreign_keys_declare_cascade_delete(
    temp_database_url: str,
) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        inspector = inspect(engine)
        insight_fks = inspector.get_foreign_keys("insights")
        memo_fks = inspector.get_foreign_keys("decision_memos")
    finally:
        engine.dispose()

    assert insight_fks[0]["constrained_columns"] == ["experiment_id"]
    assert insight_fks[0]["options"].get("ondelete") == "CASCADE"
    assert memo_fks[0]["constrained_columns"] == ["experiment_id"]
    assert memo_fks[0]["options"].get("ondelete") == "CASCADE"


def test_upgrade_from_stage_6_revision_to_head_adds_human_feedback_table(
    temp_database_url: str,
) -> None:
    """Simulates an existing Stage 6 database being upgraded to Stage 8."""
    config = _alembic_config()
    upgrade(config, _STAGE_6_REVISION)
    tables_before = _table_names(temp_database_url)
    assert not (_STAGE_8_TABLES & tables_before)
    assert _STAGE_6_TABLES <= tables_before

    upgrade(config, "head")

    tables_after = _table_names(temp_database_url)
    assert _STAGE_6_TABLES <= tables_after
    assert _STAGE_8_TABLES <= tables_after


def test_downgrade_from_head_to_stage_6_revision_drops_only_human_feedback_table(
    temp_database_url: str,
) -> None:
    config = _alembic_config()
    upgrade(config, "head")

    downgrade(config, _STAGE_6_REVISION)

    tables = _table_names(temp_database_url)
    assert _STAGE_6_TABLES <= tables
    assert not (_STAGE_8_TABLES & tables)


def test_human_feedback_unique_constraint_declared(temp_database_url: str) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        constraints = inspect(engine).get_unique_constraints("human_feedback")
    finally:
        engine.dispose()

    expected_columns = {"experiment_id", "participant_label", "variant_key"}
    assert any(set(c["column_names"]) == expected_columns for c in constraints)


def test_human_feedback_foreign_key_declares_cascade_delete(temp_database_url: str) -> None:
    upgrade(_alembic_config(), "head")
    engine = create_engine(temp_database_url)
    try:
        fks = inspect(engine).get_foreign_keys("human_feedback")
    finally:
        engine.dispose()

    assert fks[0]["constrained_columns"] == ["experiment_id"]
    assert fks[0]["options"].get("ondelete") == "CASCADE"
