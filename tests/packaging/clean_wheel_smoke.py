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
from pricing_pipeline.resources import migration_root, offline_sqlite_root, scaffold_root


def _is_outside_checkout(entry: str, checkout: Path) -> bool:
    resolved = Path(entry).resolve()
    return resolved != checkout and checkout not in resolved.parents


checkout = Path(os.environ["FORBIDDEN_CHECKOUT"]).resolve()
package_file = Path(pricing_pipeline.__file__).resolve()
assert checkout not in package_file.parents
assert (
    pricing_pipeline.__version__
    == importlib.metadata.version("superglm-pricing-pipeline")
    == "0.2.1"
)
assert len(tuple(item for item in migration_root().iterdir() if item.name.startswith("V"))) == 51
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
for name in ("pricing-builder.agent.md", "pricing-developer.agent.md"):
    assert (consumer / ".github/agents" / name).read_bytes() == (
        scaffold_root().joinpath(name).read_bytes()
    )
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
assert (package / "sql" / "README.md").read_bytes() == (
    scaffold_root().joinpath("sql", "README.md").read_bytes()
)
assert tuple(sorted(path.name for path in package.glob("*.ipynb"))) == (
    "01_data_ingestion.ipynb",
    "02_model_exploration.ipynb",
    "03_model_training.ipynb",
    "04_optional_model_editor.ipynb",
    "05_optional_manual_adjustment.ipynb",
    "06_model_deployment.ipynb",
    "07_optional_test_weekly_run.ipynb",
)
monitoring_path = package / "monitoring.py"
assert monitoring_path.is_file()
compile(monitoring_path.read_text(encoding="utf-8"), str(monitoring_path), "exec")

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


# Exercise the installed public recipe API without notebook extras or repository paths.
import pandas as pd
from superglm import Numeric, SuperGLM

from pricing_pipeline.notebook import (
    ModelRecipe,
    PricingDataset,
    PricingModelSpec,
    connect,
    register_model,
)

dataset = PricingDataset(
    pd.DataFrame(
        {"id": [1, 2, 3], "snapshot": ["2026-09-01"] * 3, "x": [0.0, 1.0, 2.0], "target": [0, 1, 2]}
    ),
    name="wheel",
    source="smoke",
    key="id",
    as_of="snapshot",
)
spec = PricingModelSpec(
    name="WHEEL",
    label="Wheel",
    model_type="frequency",
    deployment_slot="TEST",
    target="target",
    dataset=dataset,
    features=("x",),
)
recipe = ModelRecipe.from_model(
    SuperGLM(features={"x": Numeric()}, retain_fit_state=False), spec=spec
)
path = recipe.save(consumer / "model.toml")
loaded_spec, loaded_model = ModelRecipe.load(path).build(dataset=dataset)
assert ModelRecipe.from_model(loaded_model, spec=loaded_spec).sha256 == recipe.sha256
assert loaded_spec.dataset is dataset

# Run the generated file with only the installed package, from a scheduler-like cwd.
pricing = connect(mode="local", local_root=package / ".local")
try:
    register_model(
        pricing,
        PricingModelSpec(
            name="CLEAN_WHEEL_MODEL",
            label="Clean Wheel Model",
            model_type="superglm_poisson",
            deployment_slot="CLEAN_WHEEL_MODEL_UAT",
            target="claim_count",
            dataset=dataset,
            features=("x",),
        ),
        source_root=package,
    )
finally:
    pricing.engine.dispose()
scheduled_cwd = consumer.parent / "scheduled-cwd"
scheduled_cwd.mkdir()
monitoring_result = subprocess.run(
    [sys.executable, "-I", str(monitoring_path)],
    cwd=scheduled_cwd,
    check=False,
    capture_output=True,
    text=True,
)
assert monitoring_result.returncode == 1, monitoring_result.stdout + monitoring_result.stderr
logs = tuple((package / ".local" / "monitoring_logs").glob("*.log"))
assert len(logs) == 1, monitoring_result.stdout + monitoring_result.stderr
assert str(logs[0]) in monitoring_result.stdout + monitoring_result.stderr
assert "Configure load_dataset()" in logs[0].read_text(encoding="utf-8")
assert not (scheduled_cwd / ".local").exists()
