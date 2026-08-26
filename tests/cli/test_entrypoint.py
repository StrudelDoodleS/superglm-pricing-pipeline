from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pricing_pipeline.cli as cli


def test_help_is_checkout_independent_and_does_not_import_optional_stacks(monkeypatch, capsys):
    blocked = {"pyodbc", "IPython", "plotly", "azure.identity"}
    real_import = __import__

    def guarded_import(name, *args, **kwargs):
        if name in blocked or any(name.startswith(f"{item}.") for item in blocked):
            raise AssertionError(f"optional import attempted: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", guarded_import)
    assert cli.main(["--help"]) == 0
    assert "pricing-pipeline init" in capsys.readouterr().out


def test_main_uses_process_arguments_and_returns_help_code(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["pricing-pipeline", "--help"])

    assert cli.main() == 0


def test_subcommand_help_returns_zero_instead_of_raising():
    assert cli.main(["init", "--help"]) == 0


def test_invalid_command_returns_two_instead_of_raising():
    assert cli.main(["unknown"]) == 2


def test_console_and_module_forms_share_help(tmp_path: Path):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    console = subprocess.run(
        ["pricing-pipeline", "--help"], cwd=tmp_path, env=env, text=True, capture_output=True
    )
    module = subprocess.run(
        [sys.executable, "-I", "-m", "pricing_pipeline", "--help"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )
    assert console.returncode == module.returncode == 0
    assert console.stdout == module.stdout
    assert console.stderr == module.stderr == ""
