from __future__ import annotations

import base64
import csv
import hashlib
import subprocess
import tarfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.2.0"
DIST_INFO = f"airflow_superglm_builder-{VERSION}.dist-info"
SDIST_ROOT = f"airflow_superglm_builder-{VERSION}"
PACKAGE_PREFIX = "pricing_pipeline/"
FORBIDDEN_WHEEL_PREFIXES = (
    "tests/",
    "scripts/",
    "pricing_models/",
    "state/",
    "docs/",
    "tutorials/",
    "airflow/",
    "db/",
    "work_runtime/",
)
OFFLINE_SQLITE_FILES = (
    "mlops.sql",
    "pricing.sql",
    "pricing_stg.sql",
    "pricing_views.sql",
)
MIGRATION_FILES = (
    "V001__dataset_manifest_cv.sql",
    "V002__pricing_core_minimal.sql",
    "V003__superglm_staging.sql",
    "V004__compiled_rating_tables.sql",
    "V005__fremtpl_raw_model_run.sql",
    "V006__model_registry_deployments.sql",
    "V007__cv_split_sets.sql",
    "V008__compiled_band_sort_order.sql",
    "V009__current_dataset_cv_fold_view.sql",
    "V010__cv_split_runtime_metadata.sql",
    "V011__cv_split_runtime_metadata_view.sql",
    "V012__clean_pricing_schema_tables.sql",
    "V013__model_run_lineage_tables.sql",
    "V014__current_rate_prediction_proc.sql",
    "V015__rate_package_immutability.sql",
    "V016__rate_package_version_and_deploy_guards.sql",
    "V017__rate_package_source_export_id.sql",
    "V018__drop_cv_split_row_if_empty.sql",
    "V019__terminate_throw_guard_errors.sql",
    "V020__rate_package_source_file.sql",
    "V021__unify_model_name.sql",
    "V022__superglm_publication_receipt_metadata.sql",
    "V023__model_relativity_bi_views.sql",
    "V024__candidate_model_artifacts.sql",
    "V025__package_specific_scoring.sql",
    "V026__nullable_candidate_effective_date.sql",
    "V027__model_version_reservations.sql",
    "V028__staging_content_digest.sql",
    "V029__current_rate_package_scoring.sql",
    "V030__staging_content_digest_binary_collation.sql",
    "V031__model_run_parent_lineage.sql",
    "V032__model_run_rating_workbook_digest.sql",
    "V033__dataset_manifest_frame_evidence.sql",
    "V034__dataset_manifest_offset_contract.sql",
    "V035__validation_metrics_and_final_relativity_views.sql",
    "V036__model_kind_manifest_relativity.sql",
    "V037__controlled_model_monitoring.sql",
    "V038__manual_edit_model_kind.sql",
)
BASE_REQUIREMENTS = (
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
)
OPTIONAL_REQUIREMENTS = {
    "sqlserver": ("pyodbc",),
    "azure": ("azure-identity", "pyodbc"),
    "report": ("plotly>=6.9", "scipy"),
    "notebook": ("ipykernel",),
    "scratch": ("catboost", "lightgbm", "matplotlib", "scipy", "xgboost"),
    "mlflow": ("mlflow",),
}


def _tracked_package_files() -> tuple[Path, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "src/pricing_pipeline"],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return tuple(Path(name) for name in completed.stdout.splitlines())


def _expected_wheel_files() -> set[str]:
    return {
        PACKAGE_PREFIX + path.relative_to("src/pricing_pipeline").as_posix()
        for path in _tracked_package_files()
    }


def _expected_sdist_files() -> set[str]:
    prefix = f"{SDIST_ROOT}/"
    return {
        prefix + "pyproject.toml",
        prefix + "README.md",
        prefix + "PKG-INFO",
        *{prefix + path.as_posix() for path in _tracked_package_files()},
    }


def _requirement_set(requirements: tuple[str, ...]) -> set[Requirement]:
    return {Requirement(requirement) for requirement in requirements}


def test_wheel_has_only_package_and_dist_info(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        names = archive.namelist()

    assert names
    assert all(name.startswith((PACKAGE_PREFIX, f"{DIST_INFO}/")) for name in names)
    assert not any(name.startswith(FORBIDDEN_WHEEL_PREFIXES) for name in names)
    assert len(names) == len(set(names)) == len({name.casefold() for name in names})
    assert all(not PurePosixPath(name).is_absolute() for name in names)
    assert all(".." not in PurePosixPath(name).parts for name in names)


def test_wheel_matches_tracked_package_files_byte_for_byte(wheel_path: Path):
    expected = _expected_wheel_files()
    assert all("__pycache__" not in path.parts for path in _tracked_package_files())

    with ZipFile(wheel_path) as archive:
        packaged = {name for name in archive.namelist() if name.startswith(PACKAGE_PREFIX)}
        assert packaged == expected
        for source_path in _tracked_package_files():
            member = PACKAGE_PREFIX + source_path.relative_to("src/pricing_pipeline").as_posix()
            assert archive.read(member) == (ROOT / source_path).read_bytes()


def test_wheel_contains_all_packaged_sql_resources_and_scaffold(wheel_path: Path):
    expected_resources = {
        "pricing_pipeline/resources/__init__.py",
        "pricing_pipeline/resources/scaffold/__init__.py",
        *{
            f"pricing_pipeline/resources/offline_sqlite/{name}" for name in OFFLINE_SQLITE_FILES
        },
        *{f"pricing_pipeline/resources/migrations/{name}" for name in MIGRATION_FILES},
    }
    assert len(MIGRATION_FILES) == 38

    with ZipFile(wheel_path) as archive:
        assert expected_resources <= set(archive.namelist())


def test_wheel_metadata_has_exact_project_requirements_and_extras(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        metadata = BytesParser().parsebytes(archive.read(f"{DIST_INFO}/METADATA"))

    assert metadata["Name"] == "airflow-superglm-builder"
    assert metadata["Version"] == VERSION
    assert metadata["Requires-Python"] == ">=3.14"
    assert set(metadata.get_all("Provides-Extra", [])) == set(OPTIONAL_REQUIREMENTS)

    requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
    base = {requirement for requirement in requirements if requirement.marker is None}
    assert base == _requirement_set(BASE_REQUIREMENTS)
    for extra, dependencies in OPTIONAL_REQUIREMENTS.items():
        expected = {
            Requirement(f'{dependency}; extra == "{extra}"') for dependency in dependencies
        }
        actual = {
            requirement
            for requirement in requirements
            if requirement.marker is not None and f'extra == "{extra}"' in str(requirement.marker)
        }
        assert actual == expected


def test_wheel_is_pure_python_with_universal_tag(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        wheel_metadata = BytesParser().parsebytes(archive.read(f"{DIST_INFO}/WHEEL"))

    assert wheel_metadata["Root-Is-Purelib"] == "true"
    assert wheel_metadata.get_all("Tag") == ["py3-none-any"]


def test_wheel_record_hashes_and_sizes_match_members(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        record = archive.read(f"{DIST_INFO}/RECORD").decode("utf-8")
        for path, digest, size in csv.reader(record.splitlines()):
            if not digest:
                assert path == f"{DIST_INFO}/RECORD"
                assert size == ""
                continue

            algorithm, encoded_digest = digest.split("=", maxsplit=1)
            assert algorithm == "sha256"
            contents = archive.read(path)
            padding = "=" * (-len(encoded_digest) % 4)
            assert base64.urlsafe_b64decode(encoded_digest + padding) == hashlib.sha256(
                contents
            ).digest()
            assert size == str(len(contents))


def test_sdist_is_complete_and_excludes_workspace_content(sdist_path: Path):
    with tarfile.open(sdist_path) as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        files = {member.name for member in members if member.isfile()}

    assert names
    assert all(name == SDIST_ROOT or name.startswith(f"{SDIST_ROOT}/") for name in names)
    expected = _expected_sdist_files()
    assert expected <= files
    assert files <= expected | {f"{SDIST_ROOT}/.gitignore"}
    forbidden_roots = {
        "pricing_pipeline",
        "pricing_models",
        "state",
        ".venv",
        "dist",
    }
    relative_parts = [PurePosixPath(name).parts[1:] for name in names if name != SDIST_ROOT]
    assert not any(parts and parts[0] in forbidden_roots for parts in relative_parts)
    assert not any(name.endswith((".tar.gz", ".whl")) for name in names)
