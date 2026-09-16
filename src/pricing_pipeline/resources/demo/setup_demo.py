"""Start the local demo database, apply the packaged schema and seed source data.

Run once before the notebooks. Rerunning preserves the database and model history.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import secrets
import shutil
import socket
import subprocess
import time

from demo_sql_runtime import DATABASE, ROOT, get_engine
from dotenv import dotenv_values
from sqlalchemy import text

DEFAULT_SQL_PORT = 14339


def require_demo_dependencies():
    """Explain a missing notebook or SQL driver before creating any demo state."""
    missing = [name for name in ("ipykernel", "pymssql") if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError(
            f"Missing demo dependencies: {', '.join(missing)}. "
            "Install superglm-pricing-pipeline with its [demo] extra in this Python environment, "
            "then rerun setup_demo.py."
        )


def available_port():
    """Prefer the usual demo port, choosing a free port for another demo copy."""
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", DEFAULT_SQL_PORT))
        except OSError:
            listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def register_notebook_kernel():
    """Give notebooks a named kernel using this setup's Python environment."""
    from ipykernel.kernelspec import install

    install(
        user=True,
        kernel_name="pricing-sql-demo",
        display_name="Pricing SQL demo",
    )
    print("Notebook kernel: Pricing SQL demo.")


def ensure_environment():
    """Create a local demo password without replacing an existing one."""
    path = ROOT / ".env"
    if not path.exists():
        with path.open("x", encoding="utf-8") as handle:
            handle.write(f"DEMO_SQL_PORT={available_port()}\n")
            handle.write("MSSQL_SA_PASSWORD=Demo_" + secrets.token_hex(18) + "_9a!\n")
        path.chmod(0o600)
    return dotenv_values(path)


def start_server_if_needed(port):
    """Use the existing local listener, or start the included Docker service."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return
    except OSError:
        pass
    if not shutil.which("docker"):
        raise RuntimeError(
            "SQL Server is not listening on the demo port and Docker is unavailable. "
            "Start Docker Desktop or Docker Engine, then rerun setup_demo.py. "
            "Alternatively start a local SQL Server with the login and port in .env."
        )
    settings = dotenv_values(ROOT / ".env")
    environment = {
        **os.environ,
        "DEMO_SQL_PORT": str(port),
        "MSSQL_SA_PASSWORD": settings["MSSQL_SA_PASSWORD"],
    }
    subprocess.run(
        ["docker", "compose", "up", "-d", "sqlserver"], cwd=ROOT, check=True, env=environment
    )


def wait_for_server():
    engine = get_engine("master")
    deadline = time.monotonic() + 120
    try:
        while True:
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                return
            except Exception:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)
    finally:
        engine.dispose()


def prepare_database():
    """Create only this demo database and apply migrations without dropping data."""
    from pricing_pipeline.infra.migrations import apply_migrations
    from pricing_pipeline.infra.runtime import runtime_from_module

    engine = get_engine("master")
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            exists = connection.execute(text("SELECT DB_ID(:name)"), {"name": DATABASE}).scalar()
            if exists is None:
                connection.exec_driver_sql("CREATE DATABASE [PricingNotebookDemo]")
    finally:
        engine.dispose()
    engine = runtime_from_module("demo_sql_runtime").get_engine()
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT DB_NAME()")).scalar_one() != DATABASE:
                raise RuntimeError("The runtime did not select the dedicated demo database.")
        applied = apply_migrations(engine)
        print(f"Database: {DATABASE}. Applied {len(applied)} migrations.")
        seed_source(engine)
    finally:
        engine.dispose()


def seed_source(engine):
    """Keep two synthetic snapshots in SQL so 01 and monitoring.py read SQL."""
    import pandas as pd
    from demo_data import synthetic_burn_cost
    from sqlalchemy import NVARCHAR, Float, Integer

    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT OBJECT_ID('dbo.DEMO_BURN_COST_SOURCE', 'U')")
        ).scalar()
        if exists is not None:
            count = connection.execute(
                text("SELECT COUNT(*) FROM dbo.DEMO_BURN_COST_SOURCE")
            ).scalar_one()
            if count:
                print(f"Preserved {count} source rows in dbo.DEMO_BURN_COST_SOURCE.")
                return
    baseline = synthetic_burn_cost(rows=480, seed=1701, as_of="2026-08-31")
    weekly = synthetic_burn_cost(rows=360, seed=1702, as_of="2026-09-15", monitoring=True)
    source = pd.concat([baseline, weekly], ignore_index=True)
    with engine.begin() as connection:
        source.to_sql(
            "DEMO_BURN_COST_SOURCE",
            connection,
            schema="dbo",
            index=False,
            if_exists="append",
            dtype={
                "policy_id": Integer(),
                "as_of": NVARCHAR(10),
                "region": NVARCHAR(16),
                "bonus_malus": NVARCHAR(16),
                "driver_age": Float(),
                "exposure": Float(),
                "burn_cost": Float(),
            },
        )
    print(f"Seeded {len(source)} synthetic rows in dbo.DEMO_BURN_COST_SOURCE.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stop", action="store_true", help="Stop this demo's SQL Server and keep its data."
    )
    if parser.parse_args().stop:
        subprocess.run(["docker", "compose", "stop", "sqlserver"], cwd=ROOT, check=True)
        return
    require_demo_dependencies()
    register_notebook_kernel()
    settings = ensure_environment()
    port = int(settings.get("DEMO_SQL_PORT", "14339"))
    start_server_if_needed(port)
    wait_for_server()
    prepare_database()
    print(f"SQL Server: 127.0.0.1,{port}. Login: sa. Password: .env.")
    print("Open pricing_models/burn_cost_demo/01_data_ingestion.ipynb.")


if __name__ == "__main__":
    main()
