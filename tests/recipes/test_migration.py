import sqlite3

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.publishing.recipes import resolve_recipe


def test_upgrade_preserves_historical_run(tmp_path):
    root = tmp_path / "old"
    root.mkdir()
    with sqlite3.connect(root / "pricing.sqlite") as c:
        c.executescript("""
        CREATE TABLE MODEL_RUN (
            model_run_id TEXT PRIMARY KEY, model_id INTEGER NOT NULL, model_version TEXT,
            model_kind TEXT NOT NULL DEFAULT 'RAW' CHECK (model_kind IN ('RAW', 'ROUTINE_EDIT', 'EDITOR_EDIT', 'MANUAL_EDIT')),
            export_id TEXT, manifest_id TEXT, split_set_id TEXT, rate_package_id INTEGER,
            model_name TEXT, rating_workbook_path TEXT, publication_receipt_path TEXT,
            publication_receipt_sha256 TEXT, model_artifact_path TEXT, effective_from TEXT,
            run_status TEXT, started_ts TEXT, completed_ts TEXT, created_ts TEXT, created_by TEXT,
            dag_id TEXT, airflow_run_id TEXT, mlflow_run_id TEXT
        );
        INSERT INTO MODEL_RUN(model_run_id, model_id, model_version, export_id, manifest_id,
            rate_package_id, model_name, rating_workbook_path, effective_from, run_status,
            completed_ts, created_by)
        VALUES ('old-run', 9, 'v17', 'old-export', 'old-data', 71, 'OLD', 'old.xlsx',
                '2025-01-01', 'SUCCESS', '2025-02-03 12:34:56', 'historical');
        """)
    engine, _ = open_offline_sqlite(root)
    try:
        with engine.connect() as c:
            row = c.execute(text("SELECT * FROM pricing.MODEL_RUN")).mappings().one()
            assert (row["model_run_id"], row["rate_package_id"], row["model_version"]) == (
                "old-run",
                71,
                "v17",
            )
            assert row["completed_ts"] == "2025-02-03 12:34:56"
            assert row["effective_from"] == "2025-01-01"
            assert row["recipe_status"] == "LEGACY" and row["recipe_id"] is None
            assert c.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RECIPE")).scalar_one() == 0
    finally:
        engine.dispose()


def test_recipe_constraints_and_same_model_link(fitted_case):
    pricing, model, candidate, _ = fitted_case
    with pricing.engine.begin() as c:
        recipe = resolve_recipe(
            c, model_id=model.model_id, recipe=candidate.recipe, created_by="test"
        )
    with pytest.raises(IntegrityError), pricing.engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO pricing.MODEL_RECIPE(model_id,recipe_revision,recipe_sha256,recipe_format_version,recipe_json,created_by) SELECT model_id,recipe_revision,recipe_sha256,recipe_format_version,recipe_json,created_by FROM pricing.MODEL_RECIPE"
            )
        )
    for model_id, status, reason in [
        (999, "CAPTURED", None),
        (model.model_id, "LEGACY", None),
        (model.model_id, "UNSUPPORTED", None),
    ]:
        with pytest.raises(IntegrityError), pricing.engine.begin() as c:
            c.execute(
                text("""INSERT INTO pricing.MODEL_RUN(model_run_id,model_id,model_version,export_id,manifest_id,rate_package_id,rating_workbook_path,rating_workbook_sha256,created_by,recipe_id,recipe_status,recipe_unavailable_reason)
                VALUES ('invalid',:model,'v1','bad','data',999,'bad.xlsx',:sha,'test',:recipe,:status,:reason)"""),
                {
                    "model": model_id,
                    "sha": "a" * 64,
                    "recipe": recipe.recipe_id,
                    "status": status,
                    "reason": reason,
                },
            )


def test_sqlserver_recipe_foreign_keys_use_matching_declared_types():
    import re

    from pricing_pipeline.resources import migration_root

    migrations = migration_root()
    declarations = {}
    for table, filename in (
        ("MODEL_RECIPE", "V047__model_recipes.sql"),
        ("PRICING_MODEL", "V006__model_registry_deployments.sql"),
        ("MODEL_RUN", "V005__fremtpl_raw_model_run.sql"),
    ):
        sql = migrations.joinpath(filename).read_text()
        body = sql.split(f"CREATE TABLE pricing.{table} (", 1)[1]
        declarations[table] = re.search(r"\bmodel_id\s+(\w+)", body).group(1).upper()
    assert set(declarations.values()) == {"BIGINT"}, declarations


def test_sqlserver_recipe_guard_is_status_independent_and_null_safe():
    from pricing_pipeline.resources import migration_root

    sql = migration_root().joinpath("V047__model_recipes.sql").read_text()
    trigger = sql.split("CREATE OR ALTER TRIGGER pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE", 1)[
        1
    ].split("GO", 1)[0]
    assert "historical.run_status" not in trigger
    assert "EXCEPT" in trigger  # SQL Server's set comparison treats NULLs as equal.
    assert trigger.count("COLLATE Latin1_General_100_BIN2") == 4
    for column in ("model_id", "recipe_id", "recipe_status", "recipe_unavailable_reason"):
        assert f"historical.{column}" in trigger and f"current_run.{column}" in trigger
    captured_check = sql.split("recipe_status = 'CAPTURED'", 1)[1].split("OR", 1)[0]
    assert "model_id IS NOT NULL" in captured_check
    legacy_check = sql.split("recipe_status = 'LEGACY'", 1)[1].split("OR", 1)[0]
    assert "model_id" not in legacy_check


@pytest.mark.parametrize(
    "clear_marker",
    ["run_status='FAILED'", "rate_package_id=NULL", "run_status='FAILED', rate_package_id=NULL"],
)
def test_published_recipe_cannot_be_rewritten_after_clearing_markers(fitted_case, clear_marker):
    from pricing_pipeline import notebook as api

    pricing, _, candidate, _ = fitted_case
    api.save_model_version(pricing, candidate)
    try:
        with pricing.engine.begin() as c:
            c.execute(text(f"UPDATE pricing.MODEL_RUN SET {clear_marker}"))
    except IntegrityError:
        pass  # A schema constraint may already prevent clearing the marker.
    for assignment in (
        "recipe_id=NULL,recipe_status='LEGACY'",
        "model_id=NULL",
        "recipe_unavailable_reason='changed'",
    ):
        with pytest.raises(IntegrityError), pricing.engine.begin() as c:
            c.execute(text(f"UPDATE pricing.MODEL_RUN SET {assignment}"))
    with pricing.engine.begin() as c:
        c.execute(text("UPDATE pricing.MODEL_RUN SET run_status='SUCCESS'"))
        # Equal nullable fields and unrelated audit updates remain valid.
        c.execute(
            text(
                "UPDATE pricing.MODEL_RUN SET recipe_unavailable_reason=NULL, recipe_id=recipe_id, model_id=model_id"
            )
        )
        assert (
            c.execute(text("SELECT recipe_status FROM pricing.MODEL_RUN")).scalar_one()
            == "CAPTURED"
        )


def test_reopening_sqlite_refreshes_the_old_status_dependent_guard(fitted_case, tmp_path):
    from pricing_pipeline import notebook as api

    pricing, _, candidate, _ = fitted_case
    api.save_model_version(pricing, candidate)
    with pricing.engine.begin() as c:
        # Model the older database this upgrade targets, before publication
        # automatically captured immutable monitoring baseline source identity.
        c.execute(text("DROP TRIGGER pricing.TR_MODEL_MONITORING_BASELINE_DELETE"))
        c.execute(text("DELETE FROM pricing.MODEL_MONITORING_BASELINE"))
        c.execute(text("DROP TRIGGER pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE"))
        c.execute(
            text("""CREATE TRIGGER pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE
            BEFORE UPDATE OF recipe_id ON MODEL_RUN WHEN OLD.run_status='SUCCESS'
            BEGIN SELECT RAISE(ABORT, 'old guard'); END""")
        )
    upgraded, _ = open_offline_sqlite(tmp_path / "local")
    try:
        with upgraded.begin() as c:
            c.execute(text("UPDATE pricing.MODEL_RUN SET run_status='FAILED'"))
        with pytest.raises(IntegrityError), upgraded.begin() as c:
            c.execute(text("UPDATE pricing.MODEL_RUN SET recipe_id=NULL,recipe_status='LEGACY'"))
    finally:
        upgraded.dispose()
