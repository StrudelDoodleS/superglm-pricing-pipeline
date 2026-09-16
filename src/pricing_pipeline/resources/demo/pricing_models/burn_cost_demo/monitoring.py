"""Score the current champion and save three challengers using fresh source data.

Edit the settings and load_dataset() here. Notebook 07 and the scheduler call run().
"""

from __future__ import annotations

import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pricing_pipeline.notebook import (
    PricingDataset,
    connect,
    load_registered_model,
    run_monitoring,
)

DATABASE_MODE = "remote"  # "local" or "remote"
RUNTIME_MODULE = "demo_sql_runtime"  # e.g. "project_runtime.database"; no secrets
EXPECTED_REMOTE_DATABASE = "PricingNotebookDemo"
ALLOW_REMOTE_WRITES = True  # Only the local demo database.

MODEL_NAME = "DEMO_BURN_COST"
MODEL_LABEL = "Burn cost workflow demo"
DEPLOYMENT_SLOT = "DEMO_BURN_COST_ONLY"


def load_dataset() -> PricingDataset:
    """Read the newest source snapshot from the local demo SQL Server."""
    import pandas as pd
    from demo_sql_runtime import get_engine
    from sqlalchemy import text

    engine = get_engine()
    try:
        with engine.connect() as connection:
            df = pd.read_sql_query(
                text("""
                SELECT policy_id, as_of, region, bonus_malus, driver_age, exposure, burn_cost
                FROM dbo.DEMO_BURN_COST_SOURCE
                WHERE as_of = (SELECT MAX(as_of) FROM dbo.DEMO_BURN_COST_SOURCE)
                ORDER BY policy_id
            """),
                connection,
            )
    finally:
        engine.dispose()
    return PricingDataset(
        df=df,
        name="demo_burn_cost",
        source="dbo.DEMO_BURN_COST_SOURCE",
        key="policy_id",
        as_of="as_of",
    )


def run():
    """Save four observations and three challenger packages without promotion."""

    pricing = connect(
        mode=DATABASE_MODE,
        runtime_module=RUNTIME_MODULE,
        local_root=MODEL_DIR / ".local",
        expected_remote_database=EXPECTED_REMOTE_DATABASE,
        allow_remote_writes=ALLOW_REMOTE_WRITES,
    )
    try:
        model = load_registered_model(
            pricing,
            model_name=MODEL_NAME,
            model_label=MODEL_LABEL,
            deployment_slot=DEPLOYMENT_SLOT,
            source_root=MODEL_DIR,
        )
        dataset = load_dataset()
        return run_monitoring(pricing, model=model, dataset=dataset)
    finally:
        pricing.engine.dispose()


if __name__ == "__main__":
    from pricing_pipeline.monitoring_runner import run_monitoring_script

    raise SystemExit(
        run_monitoring_script(run, log_directory=MODEL_DIR / ".local" / "monitoring_logs")
    )
