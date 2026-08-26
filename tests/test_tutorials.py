import json
from pathlib import Path

TUTORIAL_NOTEBOOK = Path("tutorials/00_basic_sql_etl_schema_walkthrough.ipynb")


def _notebook_text() -> str:
    notebook = json.loads(TUTORIAL_NOTEBOOK.read_text(encoding="utf-8"))
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") in {"markdown", "code"}
    )


def test_basic_sql_etl_notebook_teaches_connection_transform_and_load_pattern():
    text = _notebook_text()

    for expected in [
        "Basic SQL ETL and Schema Walkthrough",
        "REPO_ROOT",
        '(candidate / "pyproject.toml").is_file()',
        '(candidate / "pricing_models").is_dir()',
        "get_engine(settings, database=source_database)",
        "pd.read_sql_query",
        "transform_source_rows",
        "to_sql",
        "target_schema",
        "target_table",
        "Entra token",
    ]:
        assert expected in text
    assert "sys.path.insert" not in text


def test_basic_sql_etl_notebook_explains_schema_and_erd_files():
    text = _notebook_text()

    for expected in [
        "from pricing_pipeline.resources import migration_root",
        "migration_names = tuple(",
        "display(migration_names)",
        "docs/sql/diagrams",
        "scripts/render_schema_diagrams.py",
        "raw.FREMTPL_RAW",
        "mlops.DATASET_MANIFEST",
        "mlops.MODEL_RUN",
        "pricing.MODEL",
        "pricing.RATE_PACKAGE",
        "pricing.PREDICT_CURRENT_RATE",
    ]:
        assert expected in text


def test_basic_sql_etl_notebook_shows_result_set_transform_model_and_load_shape():
    text = _notebook_text()

    for expected in [
        "Notebook DAG: Offline Load, Train, Push, Deploy",
        "sqlite3",
        "attach_pricing_lab_schemas",
        "create_offline_schema",
        "seed_source_rows",
        "source_result_set",
        "transformed_result_set",
        "train_superglm_revision",
        "persist_model_revision",
        "deploy_rate_package",
        "create_manual_uplift_package",
        "current_deployment",
        "deployment_history",
        "MODEL_SCORE",
        "raw.FREMTPL_RAW",
        "mlops.MODEL_RUN",
        "pricing.RATE_PACKAGE",
        "pricing.MODEL_DEPLOYMENT",
        "SQLite is only the offline stand-in",
        "Azure SQL with Entra auth",
        "Postgres",
        "DuckDB",
        "DDL dialect",
    ]:
        assert expected in text


def test_basic_sql_etl_notebook_explains_model_revision_and_deployment_rules():
    text = _notebook_text()

    for expected in [
        "What Counts As A Model Revision",
        "Changed feature list",
        "Changed training SQL or dataset window",
        "Changed preprocessing",
        "Changed model class or hyperparameters",
        "Manual 10% Uplift Package",
        "deployed package changes",
        "historical packages remain",
    ]:
        assert expected in text
