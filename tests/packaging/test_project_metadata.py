from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

import pricing_pipeline

ROOT = Path(__file__).resolve().parents[2]


def _project() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_project_uses_hatchling_and_only_the_src_package():
    config = _project()
    assert config["build-system"] == {
        "requires": ["hatchling"],
        "build-backend": "hatchling.build",
    }
    assert config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/pricing_pipeline"
    ]
    assert "pythonpath" not in config["tool"]["pytest"]["ini_options"]
    assert (ROOT / "src/pricing_pipeline/__init__.py").is_file()
    assert not (ROOT / "pricing_pipeline").exists()


def test_distribution_metadata_and_runtime_version_have_one_authority():
    project = _project()["project"]
    assert project["name"] == "airflow-superglm-builder"
    assert project["version"] == "0.2.0"
    assert project["requires-python"] == ">=3.14"
    assert (
        pricing_pipeline.__version__
        == importlib.metadata.version("airflow-superglm-builder")
        == "0.2.0"
    )


def test_dependency_contract_is_exact():
    project = _project()["project"]
    assert project["dependencies"] == [
        "joblib",
        "numpy",
        "openpyxl",
        "packaging",
        "pandas",
        "pyarrow>=23.0.1",
        "pydantic>=2.13,<3",
        "python-dotenv",
        "scikit-learn",
        "sqlalchemy",
        "superglm>=0.26,<0.27",
    ]
    assert project["optional-dependencies"] == {
        "sqlserver": ["pyodbc"],
        "azure": ["azure-identity", "pyodbc"],
        "report": ["plotly>=6.9", "scipy"],
        "notebook": ["ipykernel"],
        "scratch": ["catboost", "lightgbm", "matplotlib", "scipy", "xgboost"],
        "mlflow": ["mlflow"],
    }
