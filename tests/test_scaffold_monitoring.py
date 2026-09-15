from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from pricing_pipeline.notebook import PricingModelSpec, connect, register_model
from pricing_pipeline.scaffold.config import ScaffoldOptions
from pricing_pipeline.scaffold.service import scaffold_pricing_model


def _scaffold(root: Path, **overrides) -> Path:
    scaffold_pricing_model(
        ScaffoldOptions(
            model_name="WEEKLY_MODEL",
            target_name="claim_count",
            root=root,
            **overrides,
        )
    )
    return root / "pricing_models" / "weekly_model"


def _load_module(path: Path):
    assert path.is_file(), "scaffolding must generate the schedulable monitoring.py file"
    spec = importlib.util.spec_from_file_location("generated_weekly_monitoring", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _register_local_model(package: Path) -> None:
    pricing = connect(mode="local", local_root=package / ".local")
    try:
        register_model(
            pricing,
            PricingModelSpec(
                name="WEEKLY_MODEL",
                label="Weekly Model",
                target="claim_count",
                features=("feature_1",),
                dataset_name="weekly_frame",
                source_system="test",
                pk_columns=("row_id",),
                data_as_of_column="data_as_of",
                model_type="superglm_poisson",
                deployment_slot="WEEKLY_MODEL_UAT",
            ),
            source_root=package,
        )
    finally:
        pricing.engine.dispose()


@pytest.mark.parametrize(
    ("database_mode", "runtime_module", "expected_database", "model_label", "slot"),
    [
        ("local", None, "", "Weekly Model", "WEEKLY_MODEL_UAT"),
        (
            "remote",
            "project_runtime.__RUNTIME_MODULE__",
            'quoted "database" __EXPECTED_REMOTE_DATABASE_LITERAL__',
            'Müller "model"\n__MODEL_LABEL__',
            'slot"]; raise RuntimeError("not data") # __DEPLOYMENT_SLOT__',
        ),
    ],
)
def test_generated_monitoring_renders_literals_and_resolves_its_own_project(
    tmp_path, monkeypatch, database_mode, runtime_module, expected_database, model_label, slot
):
    root = tmp_path / 'project "with quotes"'
    package = _scaffold(
        root,
        database_mode=database_mode,
        runtime_module=runtime_module,
        expected_remote_database=expected_database,
        model_label=model_label,
        deployment_slot=slot,
    )
    outside = tmp_path / "unrelated"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setattr(sys, "path", sys.path.copy())

    module = _load_module(package / "monitoring.py")

    assert module.MODEL_DIR == package
    assert module.PROJECT_ROOT == root
    assert str(root) in sys.path
    assert module.DATABASE_MODE == database_mode
    assert module.RUNTIME_MODULE == runtime_module
    assert module.EXPECTED_REMOTE_DATABASE == expected_database
    assert module.ALLOW_REMOTE_WRITES is False
    assert module.MODEL_NAME == "WEEKLY_MODEL"
    assert module.MODEL_LABEL == model_label
    assert module.DEPLOYMENT_SLOT == slot
    assert not (package / ".local").exists()


def test_monitoring_upgrade_preserves_every_existing_file_and_analyst_edits(tmp_path):
    package = tmp_path / "pricing_models" / "weekly_model"
    (package / "sql").mkdir(parents=True)
    old_names = (
        "__init__.py",
        "01_data_ingestion.ipynb",
        "02_model_exploration.ipynb",
        "03_model_training.ipynb",
        "04_model_editor.ipynb",
        "05_manual_adjustment.ipynb",
        "06_model_deployment.ipynb",
        "sql/README.md",
        "sql/current_source.sql",
    )
    before = {}
    for name in old_names:
        path = package / name
        before[path] = f"Completed analyst work in {name}\r\n".encode()
        path.write_bytes(before[path])

    result = scaffold_pricing_model(
        ScaffoldOptions(model_name="WEEKLY_MODEL", target_name="claim_count", root=tmp_path)
    )

    assert set(result.created_files) == {
        package / "07_model_monitoring.ipynb",
        package / "monitoring.py",
    }
    for path, original in before.items():
        assert path.read_bytes() == original
    for name in ("monitoring.py", "07_model_monitoring.ipynb"):
        path = package / name
        path.write_bytes(path.read_bytes() + b"\n# analyst edit\n")
        before[path] = path.read_bytes()

    repeated = scaffold_pricing_model(
        ScaffoldOptions(model_name="WEEKLY_MODEL", target_name="claim_count", root=tmp_path)
    )

    assert repeated.created_files == ()
    assert all(path.read_bytes() == original for path, original in before.items())
    assert not (package / ".local").exists()


def test_unconfigured_monitoring_rejects_old_ingestion_data_and_disposes_engine(
    tmp_path, monkeypatch
):
    package = _scaffold(tmp_path)
    _register_local_model(package)
    (package / ".local" / "dataset.joblib").write_bytes(b"old ingestion artifact must not load")
    monkeypatch.setattr(sys, "path", sys.path.copy())
    module = _load_module(package / "monitoring.py")
    disposed = []
    on_dispose = disposed.append
    event.listen(Engine, "engine_disposed", on_dispose)
    try:
        with pytest.raises(RuntimeError, match=r"load_dataset\(\).*monitoring\.py"):
            module.run()
    finally:
        event.remove(Engine, "engine_disposed", on_dispose)

    assert len(disposed) == 1


def test_generated_monitoring_script_runs_from_an_unrelated_directory(tmp_path):
    package = _scaffold(tmp_path / "consumer")
    _register_local_model(package)
    script = package / "monitoring.py"
    assert script.is_file(), "scaffolding must generate a Python file for the scheduler"
    # The source loader is the one analyst edit. Its import must resolve from PROJECT_ROOT.
    project_source = package.parent.parent / "current_source.py"
    project_source.write_text(
        'def load():\n    raise RuntimeError("fresh source reached from another cwd")\n',
        encoding="utf-8",
    )
    source = script.read_text(encoding="utf-8")
    loader_start = source.index("def load_dataset(")
    run_start = source.index("\ndef run(", loader_start)
    script.write_text(
        source[:loader_start]
        + "def load_dataset():\n    from current_source import load\n    return load()\n\n"
        + source[run_start:],
        encoding="utf-8",
    )
    outside = tmp_path / "unrelated"
    outside.mkdir()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=outside,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    logs = tuple((package / ".local" / "monitoring_logs").glob("*.log"))
    assert len(logs) == 1, completed.stdout + completed.stderr
    assert "fresh source reached from another cwd" in logs[0].read_text(encoding="utf-8")
    assert str(logs[0]) in completed.stdout + completed.stderr
    assert not (outside / ".local").exists()


def test_monitoring_notebook_reloads_the_shared_module_and_displays_each_report(
    tmp_path, monkeypatch, capsys
):
    package = _scaffold(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\n', encoding="utf-8")
    notebook_path = package / "07_model_monitoring.ipynb"
    assert notebook_path.is_file(), "scaffolding must generate the monitoring notebook"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    ]
    script = package / "monitoring.py"
    # Substitute a completed run to exercise the notebook without publishing a real model.
    report_module = (
        "from pathlib import Path\n"
        "from types import SimpleNamespace\n"
        "import pandas as pd\n"
        "MODEL_DIR = Path(__file__).resolve().parent\n"
        "def run():\n"
        "    return SimpleNamespace(manifest_id=MANIFEST, **{\n"
        "        field: pd.DataFrame({'field': [field], 'manifest': [MANIFEST]})\n"
        "        for field in ('runs', 'metrics', 'issues', 'drift')})\n"
    )
    script.write_text(report_module + 'MANIFEST = "first"\n', encoding="utf-8")
    monkeypatch.chdir(package)
    monkeypatch.setattr(sys, "path", sys.path.copy())
    module_names = (
        "pricing_models",
        "pricing_models.weekly_model",
        "pricing_models.weekly_model.monitoring",
    )
    for name in module_names:
        monkeypatch.delitem(sys.modules, name, raising=False)
    displayed = []
    namespace = {"display": displayed.append}
    try:
        for cell in code_cells:
            exec(  # noqa: S102 - execute the generated notebook against a controlled report
                compile(cell, "07_model_monitoring.ipynb", "exec"), namespace
            )
        assert namespace["report"].manifest_id == "first"
        script.write_text(report_module + 'MANIFEST = "second updated run"\n', encoding="utf-8")
        displayed.clear()
        for cell in code_cells:
            exec(  # noqa: S102 - verify that rerunning the notebook reloads module edits
                compile(cell, "07_model_monitoring.ipynb", "exec"), namespace
            )
        assert namespace["report"].manifest_id == "second updated run"
    finally:
        for name in reversed(module_names):
            sys.modules.pop(name, None)

    tables = [value for value in displayed if isinstance(value, pd.DataFrame)]
    assert [value.iloc[0]["field"] for value in tables] == ["runs", "metrics", "issues", "drift"]
    assert all(value.iloc[0]["manifest"] == "second updated run" for value in tables)
    output = capsys.readouterr().out
    assert str(script) in output
    assert sys.executable in output
