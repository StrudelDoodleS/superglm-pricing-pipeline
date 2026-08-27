from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from pricing_pipeline import cli

TEMPLATE = """# Connection names only. Keep credentials in the private runtime module or its secret provider.

[notebook_defaults]
database_mode = "local"
runtime_module = ""
expected_remote_database = ""

[manual_edit_defaults]
source_selector = "deployed"
carry_forward = true
"""
EXPECTED_NOTEBOOKS = (
    "01_data_ingestion.ipynb",
    "02_model_training.ipynb",
    "03_model_editor.ipynb",
    "04_manual_adjustment.ipynb",
    "05_model_deployment.ipynb",
    "99_scratch_work.ipynb",
)


def _project(root: Path) -> None:
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "consumer"\n', encoding="utf-8")


def _assert_notebook_is_clean_and_compiles(path: Path) -> None:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        compile("".join(cell["source"]), f"{path}:cell-{index}", "exec")
        assert cell["execution_count"] is None
        assert cell["outputs"] == []


def test_init_creates_only_the_packaged_toml_from_an_unrelated_cwd(
    tmp_path: Path, monkeypatch, capsys
):
    root = tmp_path / "model-repo"
    unrelated = tmp_path / "unrelated"
    _project(root)
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    assert cli.main(["init", "--root", str(root)]) == 0

    config = root / "pricing_scaffold.toml"
    assert config.read_text(encoding="utf-8") == TEMPLATE
    assert {path.name for path in root.iterdir()} == {"pyproject.toml", "pricing_scaffold.toml"}
    assert not (root / "uv.lock").exists()
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == str(config.resolve())
    assert "edit" in lines[1].casefold()
    assert lines[2] == (
        "pricing-pipeline scaffold --model-name CLAIM_FREQUENCY --target-name claim_count"
    )


def test_init_is_idempotent_without_changing_bytes_or_mtime(tmp_path: Path):
    root = tmp_path / "model-repo"
    _project(root)
    assert cli.main(["init", "--root", str(root)]) == 0
    config = root / "pricing_scaffold.toml"
    original = config.read_bytes()
    fixed_mtime_ns = 1_700_000_000_000_000_000
    config.touch()
    config.chmod(0o644)
    os.utime(config, ns=(fixed_mtime_ns, fixed_mtime_ns))

    assert cli.main(["init", "--root", str(root)]) == 0

    assert config.read_bytes() == original
    assert config.stat().st_mtime_ns == fixed_mtime_ns


@pytest.mark.parametrize("pyproject_kind", ("missing", "symlink"))
def test_init_rejects_missing_or_symlinked_pyproject_without_creating_config(
    tmp_path: Path, pyproject_kind: str, capsys
):
    root = tmp_path / "model-repo"
    root.mkdir()
    if pyproject_kind == "symlink":
        external = tmp_path / "external-pyproject.toml"
        external.write_text('[project]\nname = "external"\n', encoding="utf-8")
        (root / "pyproject.toml").symlink_to(external)

    assert cli.main(["init", "--root", str(root)]) == 2

    assert not (root / "pricing_scaffold.toml").exists()
    assert "regular non-symlink pyproject.toml" in capsys.readouterr().err


@pytest.mark.parametrize("config_kind", ("malformed", "directory", "symlink"))
def test_init_rejects_unsafe_existing_config_without_overwriting(
    tmp_path: Path, config_kind: str, capsys
):
    root = tmp_path / "model-repo"
    _project(root)
    config = root / "pricing_scaffold.toml"
    external = tmp_path / "external.toml"
    malformed_before = None
    malformed_mtime_ns = None
    if config_kind == "malformed":
        config.write_text("not valid = [\n", encoding="utf-8")
        fixed_mtime_ns = 1_700_000_000_000_000_000
        os.utime(config, ns=(fixed_mtime_ns, fixed_mtime_ns))
        malformed_before = config.read_bytes()
        malformed_mtime_ns = config.stat().st_mtime_ns
    elif config_kind == "directory":
        config.mkdir()
    else:
        external.write_text(TEMPLATE, encoding="utf-8")
        config.symlink_to(external)
    before = external.read_bytes() if external.exists() else None

    assert cli.main(["init", "--root", str(root)]) == 2

    assert config.is_dir() if config_kind == "directory" else config.exists()
    if before is not None:
        assert external.read_bytes() == before
    if malformed_before is not None:
        assert config.read_bytes() == malformed_before
        assert config.stat().st_mtime_ns == malformed_mtime_ns
    assert "error:" in capsys.readouterr().err


def test_installed_scaffold_requires_the_initialized_default_config(tmp_path: Path, capsys):
    root = tmp_path / "model-repo"
    _project(root)

    assert (
        cli.main(
            [
                "scaffold",
                "--model-name",
                "CLAIM_FREQUENCY",
                "--target-name",
                "claim_count",
                "--root",
                str(root),
            ]
        )
        == 2
    )

    assert not (root / "pricing_models").exists()
    assert f"pricing-pipeline init --root {root.resolve()}" in capsys.readouterr().err


def test_installed_scaffold_with_explicit_config_requires_a_project_root(tmp_path: Path, capsys):
    root = tmp_path / "not-a-model-repo"
    root.mkdir()
    config = tmp_path / "explicit.toml"
    config.write_text(TEMPLATE, encoding="utf-8")

    assert (
        cli.main(
            [
                "scaffold",
                "--model-name",
                "CLAIM_FREQUENCY",
                "--target-name",
                "claim_count",
                "--root",
                str(root),
                "--config",
                str(config),
            ]
        )
        == 2
    )

    error = capsys.readouterr().err
    assert "regular non-symlink pyproject.toml" in error
    assert "failed unexpectedly" not in error
    assert {path.name for path in root.iterdir()} == set()


def test_installed_scaffold_reuses_the_exact_six_notebook_workflow(tmp_path: Path, capsys):
    root = tmp_path / "model-repo"
    _project(root)
    assert cli.main(["init", "--root", str(root)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "scaffold",
                "--model-name",
                "CLAIM_FREQUENCY",
                "--target-name",
                "claim_count",
                "--root",
                str(root),
            ]
        )
        == 0
    )

    package = root / "pricing_models" / "claim_frequency"
    expected = (package / "__init__.py", *(package / name for name in EXPECTED_NOTEBOOKS))
    assert tuple(sorted(path.name for path in package.iterdir())) == tuple(
        sorted(path.name for path in expected)
    )
    for notebook in expected[1:]:
        _assert_notebook_is_clean_and_compiles(notebook)
    assert capsys.readouterr().out.splitlines() == [str(path.resolve()) for path in expected]


def test_installed_scaffold_reports_a_managed_parent_file_as_a_user_precondition(
    tmp_path: Path, capsys
):
    root = tmp_path / "model-repo"
    _project(root)
    assert cli.main(["init", "--root", str(root)]) == 0
    capsys.readouterr()
    managed_parent = root / "pricing_models"
    sentinel = b"do not replace this file\n"
    managed_parent.write_bytes(sentinel)

    assert (
        cli.main(
            [
                "scaffold",
                "--model-name",
                "CLAIM_FREQUENCY",
                "--target-name",
                "claim_count",
                "--root",
                str(root),
            ]
        )
        == 2
    )

    error = capsys.readouterr().err
    assert "pricing_models" in error
    assert "directory" in error
    assert "failed unexpectedly" not in error
    assert managed_parent.read_bytes() == sentinel
    assert {path.name for path in root.iterdir()} == {
        "pricing_models",
        "pricing_scaffold.toml",
        "pyproject.toml",
    }


def test_installed_scaffold_force_reports_an_output_leaf_directory_without_mutation(
    tmp_path: Path, capsys
):
    root = tmp_path / "model-repo"
    _project(root)
    assert cli.main(["init", "--root", str(root)]) == 0
    capsys.readouterr()
    package = root / "pricing_models" / "claim_frequency"
    output_leaf = package / "__init__.py"
    output_leaf.mkdir(parents=True)
    sentinel = output_leaf / "keep.txt"
    sentinel_bytes = b"do not replace this directory or its contents\n"
    sentinel.write_bytes(sentinel_bytes)
    fixed_mtime_ns = 1_700_000_000_000_000_000
    os.utime(sentinel, ns=(fixed_mtime_ns, fixed_mtime_ns))

    assert (
        cli.main(
            [
                "scaffold",
                "--model-name",
                "CLAIM_FREQUENCY",
                "--target-name",
                "claim_count",
                "--root",
                str(root),
                "--force",
            ]
        )
        == 2
    )

    error = capsys.readouterr().err
    assert "pricing_models" in error
    assert "directory" in error
    assert "failed unexpectedly" not in error
    assert output_leaf.is_dir()
    assert {path.name for path in output_leaf.iterdir()} == {"keep.txt"}
    assert sentinel.read_bytes() == sentinel_bytes
    assert sentinel.stat().st_mtime_ns == fixed_mtime_ns
    assert {path.name for path in package.iterdir()} == {"__init__.py"}
    assert {path.name for path in root.iterdir()} == {
        "pricing_models",
        "pricing_scaffold.toml",
        "pyproject.toml",
    }


def test_installed_scaffold_force_preflights_all_outputs_before_writing(tmp_path: Path, capsys):
    root = tmp_path / "model-repo"
    _project(root)
    assert cli.main(["init", "--root", str(root)]) == 0
    assert (
        cli.main(
            [
                "scaffold",
                "--model-name",
                "CLAIM_FREQUENCY",
                "--target-name",
                "claim_count",
                "--root",
                str(root),
            ]
        )
        == 0
    )
    capsys.readouterr()

    package = root / "pricing_models" / "claim_frequency"
    earlier_output = package / "01_data_ingestion.ipynb"
    earlier_bytes = b"held analyst notebook\n"
    earlier_output.write_bytes(earlier_bytes)
    fixed_mtime_ns = 1_700_000_000_000_000_000
    os.utime(earlier_output, ns=(fixed_mtime_ns, fixed_mtime_ns))
    later_output = package / "05_model_deployment.ipynb"
    later_output.unlink()
    later_output.mkdir()
    sentinel = later_output / "keep.txt"
    sentinel.write_bytes(b"keep this directory\n")

    assert (
        cli.main(
            [
                "scaffold",
                "--model-name",
                "CLAIM_FREQUENCY",
                "--target-name",
                "claim_count",
                "--root",
                str(root),
                "--force",
            ]
        )
        == 2
    )

    error = capsys.readouterr().err
    assert "05_model_deployment.ipynb" in error
    assert "regular file" in error
    assert "failed unexpectedly" not in error
    assert earlier_output.read_bytes() == earlier_bytes
    assert earlier_output.stat().st_mtime_ns == fixed_mtime_ns
    assert later_output.is_dir()
    assert sentinel.read_bytes() == b"keep this directory\n"


def test_init_does_not_import_optional_runtime_stacks(tmp_path: Path, monkeypatch):
    root = tmp_path / "model-repo"
    _project(root)
    blocked = {
        "IPython",
        "azure",
        "jupyter",
        "plotly",
        "pricing_pipeline.reporting",
        "pyodbc",
        "superglm",
    }
    real_import = __import__

    def guarded_import(name, *args, **kwargs):
        if name in blocked or any(name.startswith(f"{item}.") for item in blocked):
            raise AssertionError(f"optional import attempted: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", guarded_import)

    assert cli.main(["init", "--root", str(root)]) == 0
