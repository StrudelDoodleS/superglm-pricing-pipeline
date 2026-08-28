from __future__ import annotations

import base64
import csv
import hashlib
import subprocess
import tarfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import pytest

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.2.1"
DIST_INFO = f"superglm_pricing_pipeline-{VERSION}.dist-info"
SDIST_ROOT = f"superglm_pricing_pipeline-{VERSION}"
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
RESOURCE_PREFIX = "pricing_pipeline/resources/"
MIGRATIONS_PREFIX = f"{RESOURCE_PREFIX}migrations/"
OFFLINE_SQLITE_PREFIX = f"{RESOURCE_PREFIX}offline_sqlite/"
SCAFFOLD_PREFIX = f"{RESOURCE_PREFIX}scaffold/"
SCAFFOLD_NOTEBOOK_FILES = (
    "01_data_ingestion.ipynb",
    "02_model_exploration.ipynb",
    "03_model_training.ipynb",
    "04_model_editor.ipynb",
    "05_manual_adjustment.ipynb",
    "06_model_deployment.ipynb",
)
SCAFFOLD_TEMPLATE = b"""# Connection names only. Keep credentials in the private runtime module or its secret provider.

[notebook_defaults]
database_mode = "local"
runtime_module = ""
expected_remote_database = ""

[manual_edit_defaults]
source_selector = "deployed"
carry_forward = true
"""
CACHE_DIRECTORY_NAMES = {
    ".cache",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "cache",
}
CACHE_FILENAMES = {".cache"}
ENVIRONMENT_FILENAMES = {
    "environment.json",
    "environment.toml",
    "environment.yaml",
    "environment.yml",
}
SECRET_KEY_FILENAMES = {"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa", ".netrc", ".pypirc"}
ALWAYS_BLOCK_NAME_TOKENS = {"credential", "credentials", "secret", "secrets"}
ALWAYS_BLOCK_NAME_MARKERS = {
    ("api", "key"),
    ("apikey",),
    ("private", "key"),
    ("privatekey",),
    ("service", "account"),
    ("serviceaccount",),
}
GENERIC_TOKEN_MARKERS = {"token", "tokens"}
PUBLIC_NAME_MARKERS = {
    ("ca",),
    ("public", "cert"),
    ("public", "certificate"),
    ("public", "key"),
    ("publiccert",),
    ("publiccertificate",),
    ("publickey",),
}
CODE_SUFFIXES = {".py", ".pyi"}
INTERFACE_FILENAMES = {"py.typed"}
DIST_INFO_FILENAMES = {"METADATA", "WHEEL", "RECORD", "entry_points.txt"}
CANONICAL_CREDENTIAL_STORE_PATHS = {
    (".aws", "credentials"),
    (".azure", "accesstokens.json"),
    (".config", "gcloud", "application_default_credentials.json"),
    (".docker", "config.json"),
    (".kube", "config"),
}


def _assert_wheel_member_layout(names: list[str]) -> None:
    assert names
    assert all(name.startswith((PACKAGE_PREFIX, f"{DIST_INFO}/")) for name in names)
    assert not any(name.startswith(FORBIDDEN_WHEEL_PREFIXES) for name in names)
    assert len(names) == len(set(names)) == len({name.casefold() for name in names})
    assert all(not PurePosixPath(name).is_absolute() for name in names)
    assert all(".." not in PurePosixPath(name).parts for name in names)
    package_paths = tuple(
        PurePosixPath(name).relative_to(PACKAGE_PREFIX)
        for name in names
        if name.startswith(PACKAGE_PREFIX)
    )
    _assert_release_package_relative_paths(package_paths)
    _assert_resource_inventory(set(names))
    assert {name for name in names if name.startswith(f"{DIST_INFO}/")} == {
        f"{DIST_INFO}/{filename}" for filename in DIST_INFO_FILENAMES
    }


def _tracked_package_files() -> tuple[Path, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "src/pricing_pipeline"],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    paths = tuple(Path(name) for name in completed.stdout.splitlines())
    _assert_tracked_package_paths_without_pycache(paths)
    return paths


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


def _expected_resource_names() -> set[str]:
    return {
        f"{RESOURCE_PREFIX}__init__.py",
        f"{SCAFFOLD_PREFIX}__init__.py",
        f"{SCAFFOLD_PREFIX}pricing_scaffold.toml",
        *{f"{SCAFFOLD_PREFIX}notebooks/{name}" for name in SCAFFOLD_NOTEBOOK_FILES},
        *{f"{OFFLINE_SQLITE_PREFIX}{name}" for name in OFFLINE_SQLITE_FILES},
        *{f"{MIGRATIONS_PREFIX}{name}" for name in MIGRATION_FILES},
    }


def _assert_resource_inventory(names: set[str]) -> None:
    assert len(MIGRATION_FILES) == 38
    assert {
        name for name in names if name.startswith(RESOURCE_PREFIX)
    } == _expected_resource_names()


def _assert_metadata_requirements(metadata) -> None:
    requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist", [])]
    allowed = _requirement_set(BASE_REQUIREMENTS)
    for extra, dependencies in OPTIONAL_REQUIREMENTS.items():
        allowed.update(
            Requirement(f'{dependency}; extra == "{extra}"') for dependency in dependencies
        )
    assert len(requirements) == len(allowed)
    assert set(requirements) == allowed


def _assert_record_hashes_and_sizes(archive: ZipFile) -> None:
    record = archive.read(f"{DIST_INFO}/RECORD").decode("utf-8")
    rows = list(csv.reader(record.splitlines()))
    assert all(len(row) == 3 for row in rows)
    paths = [row[0] for row in rows]
    assert len(paths) == len(set(paths))
    assert set(paths) == set(archive.namelist())

    for path, digest, size in rows:
        if path == f"{DIST_INFO}/RECORD":
            assert digest == ""
            assert size == ""
            continue

        assert digest
        assert size
        algorithm, encoded_digest = digest.split("=", maxsplit=1)
        assert algorithm == "sha256"
        contents = archive.read(path)
        padding = "=" * (-len(encoded_digest) % 4)
        assert (
            base64.urlsafe_b64decode(encoded_digest + padding) == hashlib.sha256(contents).digest()
        )
        assert size == str(len(contents))


def _is_canonical_credential_store(parts: tuple[str, ...]) -> bool:
    return any(
        len(parts) >= len(store) and parts[-len(store) :] == store
        for store in CANONICAL_CREDENTIAL_STORE_PATHS
    )


def _normalized_filename_tokens(filename: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in filename.casefold().lstrip(".").replace("-", "_").replace(".", "_").split("_")
        if token
    )


def _has_compound_marker(tokens: tuple[str, ...], markers: set[tuple[str, ...]]) -> bool:
    return any(
        tokens[index : index + len(marker)] == marker
        for marker in markers
        for index in range(len(tokens) - len(marker) + 1)
    )


def _is_clearly_named_secret_material(filename: str) -> bool:
    tokens = _normalized_filename_tokens(filename)
    if set(tokens) & ALWAYS_BLOCK_NAME_TOKENS or _has_compound_marker(
        tokens, ALWAYS_BLOCK_NAME_MARKERS
    ):
        return True
    return bool(set(tokens) & GENERIC_TOKEN_MARKERS) and not _has_compound_marker(
        tokens, PUBLIC_NAME_MARKERS
    )


def _assert_safe_package_relative_paths(paths: tuple[PurePosixPath, ...]) -> None:
    for path in paths:
        lowered_parts = tuple(part.casefold() for part in path.parts)
        assert lowered_parts
        assert not any(part in CACHE_DIRECTORY_NAMES for part in lowered_parts[:-1])

        filename = lowered_parts[-1]
        suffix = PurePosixPath(filename).suffix
        assert filename not in CACHE_FILENAMES
        assert not filename.endswith((".pyc", ".pyo"))
        assert not filename.startswith(".env")
        assert filename not in ENVIRONMENT_FILENAMES
        assert filename not in SECRET_KEY_FILENAMES
        assert not _is_canonical_credential_store(lowered_parts)
        assert not (_is_clearly_named_secret_material(filename) and suffix not in CODE_SUFFIXES)


def _assert_release_package_relative_paths(paths: tuple[PurePosixPath, ...]) -> None:
    _assert_safe_package_relative_paths(paths)
    expected_resources = _expected_resource_names()
    for path in paths:
        if path.parts[0] == "resources":
            assert f"{PACKAGE_PREFIX}{path.as_posix()}" in expected_resources
            continue

        assert path.suffix in CODE_SUFFIXES or path.name in INTERFACE_FILENAMES


def _assert_tracked_package_paths_without_pycache(paths: tuple[Path, ...]) -> None:
    relative_paths = tuple(
        PurePosixPath(path.as_posix()).relative_to("src/pricing_pipeline") for path in paths
    )
    _assert_release_package_relative_paths(relative_paths)


def _metadata_with_requirements(*additional_requirements: str):
    requirements = [f"Requires-Dist: {requirement}" for requirement in BASE_REQUIREMENTS]
    for extra, dependencies in OPTIONAL_REQUIREMENTS.items():
        requirements.extend(
            f'Requires-Dist: {dependency}; extra == "{extra}"' for dependency in dependencies
        )
    return BytesParser().parsebytes(
        "\n".join(requirements + list(additional_requirements)).encode()
    )


def _record_digest(contents: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).decode().rstrip("=")


def _clean_resource_names() -> set[str]:
    return _expected_resource_names()


def test_record_validator_rejects_wheel_member_missing_from_record(tmp_path: Path):
    archive_path = tmp_path / "missing-record-entry.whl"
    tracked_contents = b"tracked"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("pricing_pipeline/tracked.py", tracked_contents)
        archive.writestr("pricing_pipeline/unlisted.py", b"unlisted")
        archive.writestr(
            f"{DIST_INFO}/RECORD",
            "\n".join(
                (
                    f"pricing_pipeline/tracked.py,sha256={_record_digest(tracked_contents)},7",
                    f"{DIST_INFO}/RECORD,,",
                )
            ),
        )

    with ZipFile(archive_path) as archive, pytest.raises(AssertionError):
        _assert_record_hashes_and_sizes(archive)


@pytest.mark.parametrize(
    "record_rows",
    (
        lambda digest: (
            f"pricing_pipeline/tracked.py,sha256={digest},7",
            f"pricing_pipeline/tracked.py,sha256={digest},7",
            f"{DIST_INFO}/RECORD,,",
        ),
        lambda digest: (
            f"pricing_pipeline/tracked.py,sha256={digest},7",
            "pricing_pipeline/not-a-member.py,sha256=not-a-real-digest,15",
            f"{DIST_INFO}/RECORD,,",
        ),
    ),
    ids=("duplicate", "extra"),
)
def test_record_validator_rejects_duplicate_or_extra_rows(tmp_path: Path, record_rows):
    archive_path = tmp_path / "malformed-record.whl"
    contents = b"tracked"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("pricing_pipeline/tracked.py", contents)
        archive.writestr(f"{DIST_INFO}/RECORD", "\n".join(record_rows(_record_digest(contents))))

    with ZipFile(archive_path) as archive, pytest.raises(AssertionError):
        _assert_record_hashes_and_sizes(archive)


def test_resource_inventory_rejects_unexpected_migration_and_offline_sql_file():
    names = _clean_resource_names() | {
        "pricing_pipeline/resources/migrations/V039__unreviewed.sql",
        "pricing_pipeline/resources/offline_sqlite/extra.sql",
        "pricing_pipeline/resources/scaffold/credentials.toml",
    }

    with pytest.raises(AssertionError):
        _assert_resource_inventory(names)


def test_resource_inventory_rejects_unexpected_resource_root_file():
    with pytest.raises(AssertionError):
        _assert_resource_inventory(_clean_resource_names() | {f"{RESOURCE_PREFIX}scratch.sqlite"})


@pytest.mark.parametrize(
    "path",
    (
        "src/pricing_pipeline/data/confidential_customer_extract.parquet",
        "src/pricing_pipeline/models/fitted_tariff.joblib",
        "src/pricing_pipeline/artifacts/training_rows.csv",
        "src/pricing_pipeline/state/runtime.sqlite",
        "src/pricing_pipeline/assets/unreviewed.json",
        "src/pricing_pipeline/assets/unreviewed.txt",
        "src/pricing_pipeline/assets/unreviewed.bin",
        "src/pricing_pipeline/resources/unreviewed.json",
    ),
)
def test_package_source_validator_rejects_unreviewed_release_artifacts(path: str):
    with pytest.raises(AssertionError):
        _assert_tracked_package_paths_without_pycache((Path(path),))


@pytest.mark.parametrize(
    "path",
    (
        "src/pricing_pipeline/infra/release_contract.py",
        "src/pricing_pipeline/typing/release_contract.pyi",
        "src/pricing_pipeline/py.typed",
        "src/pricing_pipeline/resources/__init__.py",
        "src/pricing_pipeline/resources/migrations/V001__dataset_manifest_cv.sql",
        "src/pricing_pipeline/resources/offline_sqlite/pricing.sql",
        "src/pricing_pipeline/resources/scaffold/__init__.py",
    ),
)
def test_package_source_validator_allows_reviewed_release_inventory(path: str):
    _assert_tracked_package_paths_without_pycache((Path(path),))


def test_metadata_validator_rejects_unknown_conditional_requirement():
    metadata = _metadata_with_requirements(
        'Requires-Dist: unexpected-package; python_version < "3.15"'
    )

    with pytest.raises(AssertionError):
        _assert_metadata_requirements(metadata)


@pytest.mark.parametrize(
    "path",
    (
        "src/pricing_pipeline/.env.production",
        "src/pricing_pipeline/.cache",
        "src/pricing_pipeline/cache/serialized-result.bin",
        "src/pricing_pipeline/credentials.json",
        "src/pricing_pipeline/private_key.pem",
    ),
)
def test_package_source_validator_rejects_cache_environment_and_secret_files(path: str):
    with pytest.raises(AssertionError):
        _assert_tracked_package_paths_without_pycache((Path(path),))


@pytest.mark.parametrize(
    "path",
    (
        ".aws/credentials",
        "secrets/api_token",
    ),
)
def test_package_path_classifier_rejects_extensionless_credential_material(path: str):
    with pytest.raises(AssertionError):
        _assert_safe_package_relative_paths((PurePosixPath(path),))


@pytest.mark.parametrize(
    "path",
    (
        "keys/client_private_key",
        "keys/prod-private-key.pem",
    ),
)
def test_package_path_classifier_rejects_private_key_material(path: str):
    with pytest.raises(AssertionError):
        _assert_safe_package_relative_paths((PurePosixPath(path),))


@pytest.mark.parametrize(
    "path",
    (
        "trust/public-ca.crt",
        "keys/public-signing-key.pem",
        "keys/jwt-token-public-key.pem",
    ),
)
def test_secret_material_classifier_allows_benign_public_certificate_assets(path: str):
    assert not _is_clearly_named_secret_material(PurePosixPath(path).name)


@pytest.mark.parametrize(
    "path",
    (
        "trust/public-ca.crt",
        "keys/public-signing-key.pem",
        "keys/jwt-token-public-key.pem",
    ),
)
def test_package_source_validator_rejects_unreviewed_public_certificate_assets(path: str):
    with pytest.raises(AssertionError):
        _assert_tracked_package_paths_without_pycache((Path("src/pricing_pipeline") / path,))


def test_wheel_member_validator_rejects_environment_file():
    with pytest.raises(AssertionError):
        _assert_wheel_member_layout(["pricing_pipeline/.env.production"])


@pytest.mark.parametrize(
    "filename",
    (
        "secrets.env",
        "confidential_dataset.parquet",
    ),
)
def test_wheel_member_validator_rejects_unknown_dist_info_members(filename: str):
    with pytest.raises(AssertionError):
        _assert_wheel_member_layout(
            [
                "pricing_pipeline/__init__.py",
                f"{DIST_INFO}/METADATA",
                f"{DIST_INFO}/WHEEL",
                f"{DIST_INFO}/RECORD",
                f"{DIST_INFO}/{filename}",
            ]
        )


def test_wheel_has_only_package_and_dist_info(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        names = archive.namelist()

    _assert_wheel_member_layout(names)


def test_wheel_matches_tracked_package_files_byte_for_byte(wheel_path: Path):
    expected = _expected_wheel_files()
    _assert_tracked_package_paths_without_pycache(_tracked_package_files())

    with ZipFile(wheel_path) as archive:
        packaged = {name for name in archive.namelist() if name.startswith(PACKAGE_PREFIX)}
        assert packaged == expected
        for source_path in _tracked_package_files():
            member = PACKAGE_PREFIX + source_path.relative_to("src/pricing_pipeline").as_posix()
            assert archive.read(member) == (ROOT / source_path).read_bytes()


def test_wheel_contains_the_exact_reviewed_resource_inventory(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        _assert_resource_inventory(set(archive.namelist()))
        assert archive.read(f"{SCAFFOLD_PREFIX}pricing_scaffold.toml") == SCAFFOLD_TEMPLATE


def test_wheel_metadata_has_exact_project_requirements_and_extras(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        metadata = BytesParser().parsebytes(archive.read(f"{DIST_INFO}/METADATA"))

    assert metadata["Name"] == "superglm-pricing-pipeline"
    assert metadata["Version"] == VERSION
    assert metadata["Requires-Python"] == ">=3.14"
    assert set(metadata.get_all("Provides-Extra", [])) == set(OPTIONAL_REQUIREMENTS)

    _assert_metadata_requirements(metadata)


def test_wheel_is_pure_python_with_universal_tag(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        wheel_metadata = BytesParser().parsebytes(archive.read(f"{DIST_INFO}/WHEEL"))

    assert wheel_metadata["Root-Is-Purelib"] == "true"
    assert wheel_metadata.get_all("Tag") == ["py3-none-any"]


def test_wheel_record_hashes_and_sizes_match_members(wheel_path: Path):
    with ZipFile(wheel_path) as archive:
        _assert_record_hashes_and_sizes(archive)


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
