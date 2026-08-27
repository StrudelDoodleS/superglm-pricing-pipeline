from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.2.1"


@pytest.fixture(scope="session")
def distribution_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("distribution")
    subprocess.run(
        [
            "uv",
            "build",
            "--force-pep517",
            "--sdist",
            "--out-dir",
            str(output),
            str(ROOT),
        ],
        check=True,
    )
    sdist = output / f"superglm_pricing_pipeline-{VERSION}.tar.gz"
    subprocess.run(
        [
            "uv",
            "build",
            "--force-pep517",
            "--wheel",
            "--out-dir",
            str(output),
            str(sdist),
        ],
        check=True,
    )
    return output


@pytest.fixture(scope="session")
def sdist_path(distribution_dir: Path) -> Path:
    return distribution_dir / f"superglm_pricing_pipeline-{VERSION}.tar.gz"


@pytest.fixture(scope="session")
def wheel_path(distribution_dir: Path) -> Path:
    return distribution_dir / f"superglm_pricing_pipeline-{VERSION}-py3-none-any.whl"
