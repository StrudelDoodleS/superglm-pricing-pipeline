from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from pricing_pipeline import cli


def test_demo_generates_a_clean_runnable_project_without_starting_services(
    tmp_path, monkeypatch, capsys
):
    def reject_process(*args, **kwargs):
        pytest.fail("Generating the demo must not start Docker or install dependencies")

    monkeypatch.setattr("subprocess.run", reject_process)
    root = tmp_path / "demo with spaces"

    assert cli.main(["demo", "--root", str(root)]) == 0

    files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    assert {"setup_demo.py", "demo_sql_runtime.py", "compose.yaml", "pyproject.toml"} <= files
    assert "pricing_models/burn_cost_demo/monitoring.py" in files
    assert not any(
        part in {".env", ".local", ".venv", "wheels"} for f in files for part in Path(f).parts
    )
    notebooks = sorted(root.glob("pricing_models/burn_cost_demo/*.ipynb"))
    assert len(notebooks) == 8
    for path in notebooks:
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), f"{path.name}:{index}", "exec")
                assert cell["outputs"] == []
                assert cell["execution_count"] is None
    deployment = notebooks[5].read_text(encoding="utf-8")
    assert "PACKAGE_VERSION = None" in deployment
    assert 'DEPLOYMENT_REASON = \\"\\"' in deployment
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert sys.executable in readme
    assert "__SETUP_COMMAND__" not in readme
    assert str(root) in capsys.readouterr().out


def test_separate_demos_do_not_share_the_docker_project_or_volume(tmp_path):
    projects = []
    for parent in ("one", "two"):
        root = tmp_path / parent / "demo"
        assert cli.main(["demo", "--root", str(root)]) == 0
        project = (root / "compose.yaml").read_text(encoding="utf-8").splitlines()[0]
        assert "__PROJECT_ID__" not in project
        projects.append(project)
    assert projects[0] != projects[1]


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_demo_refuses_existing_destinations_without_touching_them(tmp_path, capsys, kind):
    root = tmp_path / "existing"
    outside = tmp_path / "outside"
    outside.mkdir()
    notebook = outside / "01_data_ingestion.ipynb"
    notebook.write_bytes(b"analyst work")
    if kind == "directory":
        root.mkdir()
        (root / "keep.txt").write_bytes(b"keep")
    elif kind == "file":
        root.write_bytes(b"keep")
    else:
        root.symlink_to(outside, target_is_directory=True)

    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert cli.main(["demo", "--root", str(root)]) == 2
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert "new directory" in capsys.readouterr().err
