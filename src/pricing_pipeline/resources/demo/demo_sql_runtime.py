"""Connect this demo to SQL Server on this machine."""

from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import URL, create_engine

ROOT = Path(__file__).resolve().parent
DATABASE = "PricingNotebookDemo"


def get_engine(database=None, *, timeout=120):
    """Use the demo login from .env and refuse other database names."""
    selected = database or DATABASE
    if selected not in {DATABASE, "master"}:
        raise ValueError("This runtime only connects to PricingNotebookDemo or master.")
    config = dotenv_values(ROOT / ".env")
    password = config.get("MSSQL_SA_PASSWORD")
    if not password:
        raise RuntimeError("Run python setup_demo.py from this project's directory first.")
    url = URL.create(
        "mssql+pymssql",
        username="sa",
        password=password,
        host="127.0.0.1",
        port=int(config.get("DEMO_SQL_PORT", "14339")),
        database=selected,
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"login_timeout": 5, "timeout": timeout, "charset": "UTF-8"},
    )


def get_schema_names():
    return {"pricing": "pricing", "pricing_staging": "pricing_stg", "mlops": "mlops"}


def get_runtime_settings():
    return {
        "pricing_database": DATABASE,
        "skip_database_create": True,
        "mlflow_enabled": False,
        "rating_export_root": str(ROOT / ".local" / "rating_exports"),
        "validation_split_artifact_root": str(ROOT / ".local" / "splits"),
        "workbench_artifact_root": str(ROOT / ".local" / "artifacts"),
    }
