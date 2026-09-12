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
