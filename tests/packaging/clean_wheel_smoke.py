from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pricing_pipeline
from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.resources import migration_root, offline_sqlite_root


def _is_outside_checkout(entry: str, checkout: Path) -> bool:
    resolved = Path(entry).resolve()
    return resolved != checkout and checkout not in resolved.parents


checkout = Path(os.environ["FORBIDDEN_CHECKOUT"]).resolve()
package_file = Path(pricing_pipeline.__file__).resolve()
assert checkout not in package_file.parents
assert (
    pricing_pipeline.__version__
    == importlib.metadata.version("superglm-pricing-pipeline")
    == "0.2.0"
)
assert len(tuple(item for item in migration_root().iterdir() if item.name.startswith("V"))) == 38
assert tuple(sorted(item.name for item in offline_sqlite_root().iterdir() if item.is_file())) == (
    "mlops.sql",
    "pricing.sql",
    "pricing_stg.sql",
    "pricing_views.sql",
)
distribution = importlib.metadata.distribution("superglm-pricing-pipeline")
direct_url = distribution.read_text("direct_url.json")
if direct_url is not None:
    direct_url_payload = json.loads(direct_url)
    assert direct_url_payload.get("dir_info", {}).get("editable") is not True
    assert str(checkout) not in direct_url
assert all(_is_outside_checkout(entry, checkout) for entry in sys.path if entry)
assert importlib.util.find_spec("ipykernel") is None
assert importlib.util.find_spec("pyodbc") is None

consumer = Path.cwd()
(consumer / "pyproject.toml").write_text(
    '[project]\nname = "clean-wheel-consumer"\nversion = "0.1.0"\n',
    encoding="utf-8",
)
init_result = subprocess.run(
    [sys.executable, "-I", "-m", "pricing_pipeline", "init", "--root", str(consumer)],
    check=False,
    capture_output=True,
    text=True,
)
assert init_result.returncode == 0, init_result.stderr
assert str((consumer / "pricing_scaffold.toml").resolve()) in init_result.stdout
scaffold_result = subprocess.run(
    [
        sys.executable,
        "-I",
        "-m",
        "pricing_pipeline",
        "scaffold",
        "--model-name",
        "CLEAN_WHEEL_MODEL",
        "--target-name",
        "claim_count",
        "--root",
        str(consumer),
    ],
    check=False,
    capture_output=True,
    text=True,
)
assert scaffold_result.returncode == 0, scaffold_result.stderr
package = consumer / "pricing_models" / "clean_wheel_model"
assert tuple(sorted(path.name for path in package.glob("*.ipynb"))) == (
    "01_data_ingestion.ipynb",
    "02_model_training.ipynb",
    "03_model_editor.ipynb",
    "04_manual_adjustment.ipynb",
    "05_model_deployment.ipynb",
    "99_scratch_work.ipynb",
)

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
