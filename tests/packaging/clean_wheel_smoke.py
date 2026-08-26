from __future__ import annotations

import importlib.metadata
import json
import os
import sys
from pathlib import Path

import pricing_pipeline
from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.resources import migration_root, offline_sqlite_root

checkout = Path(os.environ["FORBIDDEN_CHECKOUT"]).resolve()
package_file = Path(pricing_pipeline.__file__).resolve()
assert checkout not in package_file.parents
assert (
    pricing_pipeline.__version__
    == importlib.metadata.version("airflow-superglm-builder")
    == "0.2.0"
)
assert len(tuple(item for item in migration_root().iterdir() if item.name.startswith("V"))) == 38
assert tuple(sorted(item.name for item in offline_sqlite_root().iterdir() if item.is_file())) == (
    "mlops.sql",
    "pricing.sql",
    "pricing_stg.sql",
    "pricing_views.sql",
)
distribution = importlib.metadata.distribution("airflow-superglm-builder")
direct_url = distribution.read_text("direct_url.json")
if direct_url is not None:
    direct_url_payload = json.loads(direct_url)
    assert direct_url_payload.get("dir_info", {}).get("editable") is not True
    assert str(checkout) not in direct_url
assert all(checkout not in Path(entry).resolve().parents for entry in sys.path if entry)

root = Path(os.environ["SMOKE_DATABASE_ROOT"])
engine, _paths = open_offline_sqlite(root)
with engine.connect() as connection:
    assert (
        connection.exec_driver_sql(
            "SELECT COUNT(*) FROM pricing.MODEL_MONITOR_VARIANT"
        ).scalar_one()
        == 4
    )
    assert (
        connection.exec_driver_sql(
            "SELECT COUNT(*) FROM pricing.V_CURRENT_DEPLOYED_RELATIVITY"
        ).scalar_one()
        == 0
    )
