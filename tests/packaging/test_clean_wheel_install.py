from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_wheel_runs_from_unrelated_directory(wheel_path, tmp_path):
    venv = tmp_path / "venv"
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    subprocess.run(
        ["uv", "venv", "--no-project", "--python", sys.executable, str(venv)],
        check=True,
    )
    python = _venv_python(venv)
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), str(wheel_path)],
        check=True,
    )
    smoke = tmp_path / "clean_wheel_smoke.py"
    smoke.write_bytes((ROOT / "tests/packaging/clean_wheel_smoke.py").read_bytes())
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        PYTHONNOUSERSITE="1",
        FORBIDDEN_CHECKOUT=str(ROOT),
        SMOKE_DATABASE_ROOT=str(tmp_path / "database"),
    )
    subprocess.run(
        [str(python), "-I", str(smoke)],
        cwd=consumer,
        env=env,
        check=True,
    )


def test_smoke_rejects_checkout_as_an_exact_sys_path_entry(wheel_path, tmp_path):
    venv = tmp_path / "venv"
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    subprocess.run(
        ["uv", "venv", "--no-project", "--python", sys.executable, str(venv)],
        check=True,
    )
    python = _venv_python(venv)
    subprocess.run(
        ["uv", "pip", "install", "--python", str(python), str(wheel_path)],
        check=True,
    )
    smoke = tmp_path / "clean_wheel_smoke.py"
    smoke.write_bytes((ROOT / "tests/packaging/clean_wheel_smoke.py").read_bytes())
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        PYTHONNOUSERSITE="1",
        FORBIDDEN_CHECKOUT=str(ROOT),
        SMOKE_DATABASE_ROOT=str(tmp_path / "database"),
        SMOKE_SCRIPT=str(smoke),
    )
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                (
                    "import os; import runpy; import sys; "
                    "sys.path.insert(0, os.environ['FORBIDDEN_CHECKOUT']); "
                    "runpy.run_path(os.environ['SMOKE_SCRIPT'], run_name='__main__')"
                ),
            ],
            cwd=consumer,
            env=env,
            check=True,
        )
