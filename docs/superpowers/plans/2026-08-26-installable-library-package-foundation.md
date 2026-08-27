# Installable Library Package Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a real `0.2.0` Hatchling wheel/sdist with a `src/` layout, one packaged SQL authority, bounded dependency extras, and a clean-room proof that the installed wheel works outside the framework checkout.

**Architecture:** Move the existing import package intact under `src/`, then expose SQL through a small `importlib.resources` boundary instead of repository-relative paths. Preserve low-level explicit-directory APIs for temporary tests, but make all canonical runtime paths use packaged resources. Prove the result by building the wheel from the sdist, validating both archives, installing the wheel into a new venv, and running SQLite from an unrelated cwd with `PYTHONPATH` removed.

**Tech Stack:** Python 3.14, uv, Hatchling/PEP 517, `importlib.metadata`, `importlib.resources`, pytest, SQLAlchemy, SQLite, ZIP/TAR inspection.

**Spec:** `docs/superpowers/specs/2026-08-26-installable-pricing-pipeline-design.md`

## Global Constraints

- Keep distribution name `airflow-superglm-builder` and import namespace `pricing_pipeline`.
- Set the first installable-library release to `0.2.0`; `pricing_pipeline.__version__` must come only from installed metadata.
- Keep `requires-python = ">=3.14"`; expanding Python support is outside this refactor.
- Use Hatchling with wheel package selection exactly `src/pricing_pipeline`.
- Bound SuperGLM to `>=0.26,<0.27`.
- Use `uv`; the locked canonical test command is `uv run --locked --all-extras python -m pytest -p no:cacheprovider`.
- Do not add a `sys.path` or pytest `pythonpath` escape hatch.
- The wheel must not contain model projects, work runtime modules, tests, scripts, documentation, state, credentials, or checkout-only SQL directories.
- SQL resources under `src/pricing_pipeline/resources/` become the only executable schema authority; explicit temporary directories remain test/development inputs only.
- This plan does not implement the public CLI, new standalone scaffold templates, identity attestations, or notebook supervisor. It reserves their package-resource interfaces and leaves the current script behavior compatible.
- Never add or inspect confidential work data; generated databases and build artifacts stay in ignored temporary directories.

---

## File Structure

### Created

- `src/pricing_pipeline/resources/__init__.py` — canonical resource traversal and temporary materialization.
- `src/pricing_pipeline/resources/scaffold/__init__.py` — reserved package location; actual versioned standalone templates arrive with the scaffold plan.
- `tests/packaging/__init__.py` — packaging-test namespace.
- `tests/packaging/conftest.py` — one session build of sdist and wheel-from-sdist.
- `tests/packaging/clean_wheel_smoke.py` — checkout-independent import/resource/SQLite smoke program.
- `tests/packaging/test_project_metadata.py` — build, dependency, version, and source-layout contract.
- `tests/packaging/test_distribution_contents.py` — archive path, payload, metadata, and `RECORD` contract.
- `tests/packaging/test_clean_wheel_install.py` — fresh-venv wheel installation and isolated execution.
- `tests/test_packaged_resources.py` — exact migration/offline inventory and runtime access.

### Moved

- `pricing_pipeline/**` → `src/pricing_pipeline/**` — preserve the complete existing namespace, including `tools/`.
- `db/migrations/*.sql` → `src/pricing_pipeline/resources/migrations/*.sql` — unchanged bytes.
- `db/offline_sqlite/*.sql` → `src/pricing_pipeline/resources/offline_sqlite/*.sql` — unchanged bytes.

### Modified

- `pyproject.toml`, `uv.lock`, `requirements.txt` — PEP 517, exact extras, lock, generated Airflow compatibility export.
- `.gitignore` — exclude local `dist/` build output.
- `src/pricing_pipeline/__init__.py` — metadata-derived version.
- `src/pricing_pipeline/infra/migrations.py` — `Path | Traversable` migration discovery.
- `src/pricing_pipeline/infra/offline_sqlite.py` — packaged offline DDL.
- `scripts/apply_schema.py`, `scripts/reset_remote_pricing_schema.py`, `scripts/render_schema_sql.py` — packaged defaults; no schema-directory environment authority.
- `scripts/export_portable_underwriter_report.py` — `src/` source inspection.
- `scripts/scaffold_pricing_model.py` and `pricing_models/mtpl_frequency/*.ipynb` — compatibility-only root detection after the source move.
- `docker-compose.yml`, `airflow/Dockerfile` — explicitly development-only source mount at `/opt/airflow/src`; no `db/` migration mount or `PRICING_SCHEMA_DIR`.
- Source/path-sensitive tests listed in Tasks 1–3.
- `README.md`, `docs/sql/README.md`, `tutorials/README.md`, `tutorials/00_basic_sql_etl_schema_walkthrough.ipynb` — installed-resource commands and no claim that `db/` is canonical.

### Removed

- Root `pricing_pipeline/` and `db/` after their contents are moved.
- Maintained duplicate executable SQL snapshots: `docs/pricing_useful_tables_ddl.sql`, `docs/pricing_useful_tables_full_ddl.sql`, and `tutorials/schema/pricing_useful_tables_ddl.sql`.

---

### Task 1: Establish the Hatchling `src/` package and exact dependency contract

**Files:**
- Create: `tests/packaging/__init__.py`
- Create: `tests/packaging/test_project_metadata.py`
- Move: `pricing_pipeline/**` → `src/pricing_pipeline/**`
- Modify: `src/pricing_pipeline/__init__.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `scripts/export_portable_underwriter_report.py`
- Modify: `tests/test_file_lock.py`
- Modify: `tests/test_migrations.py`
- Modify: `tests/test_model_agnostic_report.py`
- Modify: `tests/test_package_writer.py`
- Modify: `tests/test_repo_hygiene.py`
- Modify: `tests/test_runtime_contract.py`

**Interfaces:**
- Consumes: existing `pricing_pipeline` package and current dependency lock.
- Produces: installed `pricing_pipeline` from `src/pricing_pipeline`; `pricing_pipeline.__version__: str`; exact project extras used by all later tasks.

- [ ] **Step 1: Write the failing metadata/source-layout contract**

```python
# tests/packaging/test_project_metadata.py
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
    assert pricing_pipeline.__version__ == importlib.metadata.version(
        "airflow-superglm-builder"
    ) == "0.2.0"


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
```

- [ ] **Step 2: Run the contract and observe the expected failures**

Run:

```bash
uv run python -m pytest -p no:cacheprovider tests/packaging/test_project_metadata.py -q
```

Expected: failures for missing build backend, old version/dependencies, root package, literal `__version__`, and pytest `pythonpath`.

- [ ] **Step 3: Move the package and configure Hatchling**

Perform the mechanical move, then set the exact metadata asserted above:

```bash
mkdir -p src
git mv pricing_pipeline src/pricing_pipeline
```

Use this version implementation:

```python
# src/pricing_pipeline/__init__.py
"""Notebook-first SuperGLM pricing publication and audit tools."""

from importlib.metadata import version

__version__ = version("airflow-superglm-builder")
```

Add to `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pricing_pipeline"]
```

Set version/dependencies/extras exactly as the test requires, remove pytest's `pythonpath`, and add direct development dependencies `ruff`, `PyYAML`, and `sqlfluff>=4.2.1` alongside pytest.

- [ ] **Step 4: Repair repository-only source inspections**

Replace every literal source path in the files listed above from `pricing_pipeline/...` to `src/pricing_pipeline/...`. Change `scripts/export_portable_underwriter_report.py`'s embedded-source map to `ROOT / "src/pricing_pipeline/..."`. Do not add runtime path mutation.

- [ ] **Step 5: Regenerate and verify the lock**

Run:

```bash
uv lock
uv lock --check
uv sync --locked --all-extras
```

Inspect the `airflow-superglm-builder` lock entry and require version `0.2.0`, the bounded SuperGLM dependency, and all six extras.

- [ ] **Step 6: Run the focused and full source-layout suites**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/packaging/test_project_metadata.py \
  tests/test_repo_hygiene.py \
  tests/test_runtime_contract.py \
  tests/test_file_lock.py -q
uv run --locked --all-extras python -m pytest -p no:cacheprovider -q
```

Expected: all tests pass from the editable installed `src` package; no test config inserts the repository root for package imports.

- [ ] **Step 7: Commit the source-layout unit**

```bash
git add pyproject.toml uv.lock src scripts/export_portable_underwriter_report.py tests
git commit -m "Build pricing pipeline from src layout"
```

---

### Task 2: Package the offline SQLite DDL and bootstrap from resources

**Files:**
- Create: `src/pricing_pipeline/resources/__init__.py`
- Create: `src/pricing_pipeline/resources/scaffold/__init__.py`
- Move: `db/offline_sqlite/*.sql` → `src/pricing_pipeline/resources/offline_sqlite/*.sql`
- Modify: `src/pricing_pipeline/infra/offline_sqlite.py`
- Create: `tests/test_packaged_resources.py`
- Modify: `tests/test_offline_sqlite.py`
- Modify: `tests/test_fremtpl.py`

**Interfaces:**
- Consumes: installed `src/pricing_pipeline` from Task 1.
- Produces: `migration_root() -> Traversable`, `offline_sqlite_root() -> Traversable`, `scaffold_root() -> Traversable`, and `materialized_migration_dir() -> ContextManager[Path]`; SQLite no longer depends on checkout paths.

- [ ] **Step 1: Write failing resource and outside-cwd SQLite tests**

```python
# tests/test_packaged_resources.py
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import text

from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.resources import offline_sqlite_root


OFFLINE_NAMES = ("mlops.sql", "pricing.sql", "pricing_stg.sql", "pricing_views.sql")


def test_offline_sqlite_resource_inventory_is_exact():
    root = offline_sqlite_root()
    assert tuple(sorted(item.name for item in root.iterdir() if item.is_file())) == OFFLINE_NAMES
    assert all(root.joinpath(name).read_text(encoding="utf-8").strip() for name in OFFLINE_NAMES)


def test_offline_bootstrap_works_outside_checkout(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setenv("PRICING_SCHEMA_DIR", str(tmp_path / "poison"))

    engine, _paths = open_offline_sqlite(tmp_path / "database")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM pricing.MODEL_RUN")
        ).scalar_one() == 0
        assert connection.execute(
            text("SELECT COUNT(*) FROM pricing.MODEL_MONITOR_VARIANT")
        ).scalar_one() == 4
        assert connection.execute(
            text("SELECT COUNT(*) FROM pricing.V_CURRENT_DEPLOYED_RELATIVITY")
        ).scalar_one() == 0
```

- [ ] **Step 2: Run the new tests and observe missing resource APIs**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/test_packaged_resources.py -q
```

Expected: import failure for `pricing_pipeline.resources` or missing resource functions.

- [ ] **Step 3: Implement the resource boundary**

```python
# src/pricing_pipeline/resources/__init__.py
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path


_ROOT_PACKAGE = "pricing_pipeline.resources"


def migration_root() -> Traversable:
    return files(_ROOT_PACKAGE).joinpath("migrations")


def offline_sqlite_root() -> Traversable:
    return files(_ROOT_PACKAGE).joinpath("offline_sqlite")


def scaffold_root() -> Traversable:
    return files(_ROOT_PACKAGE).joinpath("scaffold")


@contextmanager
def materialized_migration_dir() -> Iterator[Path]:
    with as_file(migration_root()) as path:
        yield path
```

Move the four offline SQL files without editing their bytes. Keep the empty scaffold resource package as a reserved boundary; do not extract the obsolete inline notebook templates.

- [ ] **Step 4: Replace checkout-derived offline DDL paths**

In `src/pricing_pipeline/infra/offline_sqlite.py`, remove `Path(__file__).resolve().parents[2] / "db" / "offline_sqlite"`. Resolve once through `offline_sqlite_root()` and read each member with `.joinpath(name).read_text(encoding="utf-8")`. Preserve the existing SQLite transaction/upgrade behavior unchanged.

- [ ] **Step 5: Update offline tests to use package resources**

Replace direct `Path("db/offline_sqlite/pricing.sql")` reads in `tests/test_offline_sqlite.py`, `tests/test_fremtpl.py`, and `tests/test_migrations.py` with `offline_sqlite_root().joinpath("pricing.sql").read_text(encoding="utf-8")`. Tests that deliberately substitute a temporary DDL root may monkeypatch the resource-root function, not a repository constant.

- [ ] **Step 6: Run SQLite and resource verification**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/test_packaged_resources.py tests/test_offline_sqlite.py tests/test_fremtpl.py -q
```

Expected: all pass with cwd-independent resource discovery and unchanged offline schema semantics.

- [ ] **Step 7: Commit the offline-resource unit**

```bash
git add src/pricing_pipeline/resources src/pricing_pipeline/infra/offline_sqlite.py \
  tests/test_packaged_resources.py tests/test_offline_sqlite.py tests/test_fremtpl.py \
  tests/test_migrations.py
git commit -m "Package offline SQLite schema resources"
```

---
### Task 3: Make packaged SQL Server migrations the canonical authority

**Files:**
- Move: `db/migrations/*.sql` → `src/pricing_pipeline/resources/migrations/*.sql`
- Modify: `src/pricing_pipeline/infra/migrations.py`
- Modify: `scripts/apply_schema.py`
- Modify: `scripts/reset_remote_pricing_schema.py`
- Modify: `scripts/render_schema_sql.py`
- Modify: `tests/test_migrations.py`
- Modify: `tests/test_sql_server_syntax.py`
- Modify: `tests/test_apply_schema.py`
- Modify: `tests/test_reset_remote_pricing_schema.py`
- Modify: `tests/test_readme_contract.py`
- Modify: `tests/test_packaged_resources.py`

**Interfaces:**
- Consumes: `migration_root()` and `materialized_migration_dir()` from Task 2.
- Produces: `migration_files(directory: Path | Traversable | None = None) -> list[Path | Traversable]`; canonical callers pass `None`, temporary test callers may pass an explicit directory.

- [ ] **Step 1: Extend the failing inventory/default-authority tests**

Add to `tests/test_packaged_resources.py`:

```python
from pricing_pipeline.infra.migrations import migration_files
from pricing_pipeline.resources import migration_root


EXPECTED_MIGRATIONS = (
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


def test_sql_server_migration_inventory_is_exact_and_ordered(monkeypatch, tmp_path):
    monkeypatch.setenv("PRICING_SCHEMA_DIR", str(tmp_path / "poison"))
    resources = migration_files()
    assert tuple(item.name for item in resources) == EXPECTED_MIGRATIONS
    assert all(item.read_text(encoding="utf-8").strip() for item in resources)
    assert tuple(item.name for item in migration_root().iterdir() if item.is_file()) != ()
```

Also change `tests/test_apply_schema.py` and `tests/test_reset_remote_pricing_schema.py` to assert their default path comes from `materialized_migration_dir()`, and that setting `PRICING_SCHEMA_DIR` cannot redirect it.

- [ ] **Step 2: Run the resource/default tests and observe failure**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/test_packaged_resources.py tests/test_apply_schema.py \
  tests/test_reset_remote_pricing_schema.py -q
```

Expected: default migration discovery still requires a directory and scripts still derive `db/migrations` from cwd/environment.

- [ ] **Step 3: Move migrations and generalize discovery**

Move all 38 files unchanged. Implement discovery without coercing resources to `Path`:

```python
# src/pricing_pipeline/infra/migrations.py
from importlib.resources.abc import Traversable

from pricing_pipeline.resources import migration_root


MigrationEntry = Path | Traversable


def migration_files(directory: MigrationEntry | None = None) -> list[MigrationEntry]:
    root = migration_root() if directory is None else directory
    return sorted(
        (item for item in root.iterdir() if item.is_file() and item.name.startswith("V")
         and item.name.endswith(".sql")),
        key=lambda item: item.name,
    )
```

Update `apply_migrations_in_transaction()` and `apply_migrations()` to default `migrations_dir=None` and consume `.name`/`.read_text()` from either type. Preserve explicit temporary-directory behavior and SQL transaction semantics.

- [ ] **Step 4: Switch canonical scripts to a materialized packaged directory**

In `scripts/apply_schema.py`, delete `_schema_dir()`, `PRICING_SCHEMA_DIR`, and `PRICING_MIGRATIONS_DIR` handling. Wrap existing discovery/application in:

```python
from pricing_pipeline.resources import materialized_migration_dir

with materialized_migration_dir() as schema_dir:
    files = migration_files(schema_dir)
    applied = set(apply_migrations(engine, schema_dir))
```

In reset, make `--schema-dir` absent and materialize the packaged directory around `reset_and_reseed_schema()`. In schema rendering, accept `migrations_dir: Path | Traversable | None = None` and use the packaged default when omitted. Do not add the later governed development override in this slice.

- [ ] **Step 5: Convert SQL tests from repository paths to resources**

Use a helper local to `tests/test_migrations.py`:

```python
from pricing_pipeline.resources import migration_root


def _migration_text(name: str) -> str:
    return migration_root().joinpath(name).read_text(encoding="utf-8")
```

Replace every direct `Path("db/migrations/...sql").read_text(...)` with `_migration_text(...)`. Update `tests/test_sql_server_syntax.py` to iterate `migration_files()` and keep temporary-path unit tests passing explicit `tmp_path`.

- [ ] **Step 6: Run SQL resource and script suites**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/test_packaged_resources.py tests/test_migrations.py \
  tests/test_sql_server_syntax.py tests/test_apply_schema.py \
  tests/test_reset_remote_pricing_schema.py tests/test_readme_contract.py -q
```

Expected: all pass; `rg -n 'db/migrations|PRICING_SCHEMA_DIR|PRICING_MIGRATIONS_DIR' src scripts tests` finds no canonical runtime lookup.

- [ ] **Step 7: Commit the SQL Server resource unit**

```bash
git add src/pricing_pipeline/resources/migrations src/pricing_pipeline/infra/migrations.py \
  scripts/apply_schema.py scripts/reset_remote_pricing_schema.py \
  scripts/render_schema_sql.py tests
git commit -m "Load migrations from installed resources"
```

---

### Task 4: Repair development runtime paths and remove duplicate SQL authorities

**Files:**
- Modify: `scripts/scaffold_pricing_model.py`
- Modify: `pricing_models/mtpl_frequency/01_data_ingestion.ipynb`
- Modify: `pricing_models/mtpl_frequency/02_model_training.ipynb`
- Modify: `pricing_models/mtpl_frequency/03_model_editor.ipynb`
- Modify: `pricing_models/mtpl_frequency/04_manual_adjustment.ipynb`
- Modify: `pricing_models/mtpl_frequency/05_model_deployment.ipynb`
- Modify: `pricing_models/mtpl_frequency/99_scratch_work.ipynb`
- Modify: `docker-compose.yml`
- Modify: `airflow/Dockerfile`
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `docs/sql/README.md`
- Modify: `tutorials/README.md`
- Modify: `tutorials/00_basic_sql_etl_schema_walkthrough.ipynb`
- Delete: `docs/pricing_useful_tables_ddl.sql`
- Delete: `docs/pricing_useful_tables_full_ddl.sql`
- Delete: `tutorials/schema/pricing_useful_tables_ddl.sql`
- Modify: `tests/test_pricing_model_notebooks.py`
- Modify: `tests/test_scaffold_pricing_model.py`
- Modify: `tests/test_no_docker_runtime.py`
- Modify: `tests/test_tutorials.py`
- Modify: `tests/test_readme_contract.py`
- Modify: `tests/test_migrations.py`

**Interfaces:**
- Consumes: installed source package and packaged SQL resources from Tasks 1–3.
- Produces: development-only Compose source mount at `/opt/airflow/src`; generated legacy dependency export; tutorials/docs that generate or inspect authoritative resources instead of shipping copied SQL.

- [ ] **Step 1: Write compatibility and single-authority regressions**

Add assertions that:

```python
def test_no_maintained_duplicate_schema_sql_files():
    for path in (
        Path("docs/pricing_useful_tables_ddl.sql"),
        Path("docs/pricing_useful_tables_full_ddl.sql"),
        Path("tutorials/schema/pricing_useful_tables_ddl.sql"),
    ):
        assert not path.exists()


def test_compose_uses_src_development_mount_without_schema_mount():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    common = compose["x-airflow-common"]
    assert common["environment"]["PYTHONPATH"] == "/opt/airflow/src"
    assert all("/pricing_pipeline:/opt/airflow/pricing_pipeline" not in item
               for item in common["volumes"])
    assert all(":/opt/pricing/db" not in item for item in common["volumes"])
    assert "PRICING_SCHEMA_DIR" not in common["environment"]
```

Update notebook/scaffold contract tests to require repository discovery by `pyproject.toml` plus `pricing_models/`, not a root `pricing_pipeline/` directory, and to reject `sys.path` insertion.

- [ ] **Step 2: Run compatibility tests and observe stale-path failures**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/test_no_docker_runtime.py tests/test_pricing_model_notebooks.py \
  tests/test_scaffold_pricing_model.py tests/test_tutorials.py \
  tests/test_readme_contract.py -q
```

Expected: failures identify the old root-package predicate, old Compose mounts/environment, and maintained SQL copies.

- [ ] **Step 3: Repair legacy notebook/scaffold root discovery only**

Change the package-owned setup cell template and checked-in notebooks to locate the framework-development root by:

```python
PROJECT_ROOT = next(
    candidate
    for candidate in (Path.cwd().resolve(), *Path.cwd().resolve().parents)
    if (candidate / "pyproject.toml").is_file()
    and (candidate / "pricing_models").is_dir()
)
```

Do not insert it into `sys.path`; imports resolve from the uv-installed project. Do not rename/reorder these legacy notebooks in this package-foundation task.

- [ ] **Step 4: Make Compose explicitly use the moved development source**

Set development `PYTHONPATH` to `/opt/airflow/src`, mount `${AIRFLOW_PROJ_DIR:-.}/src/pricing_pipeline:/opt/airflow/src/pricing_pipeline`, remove the `db:/opt/pricing/db` mount and `PRICING_SCHEMA_DIR`, and leave a clear comment that this is the development profile. Update Docker/requirements comments so this stack is not described as the clean-wheel production proof.

Regenerate the compatibility requirements file from the lock:

```bash
uv export --locked --no-dev --no-emit-project --no-hashes \
  --extra azure --extra mlflow --extra report --extra sqlserver \
  --output-file requirements.txt
```

The generated header must remain intact; no package constraint may be hand-edited.

- [ ] **Step 5: Remove duplicate SQL and update docs/tutorials**

Delete the three maintained SQL copies. Update prose to identify `pricing_pipeline.resources.migrations` as the authority. Replace the tutorial DDL-path cell with resource discovery:

```python
from pricing_pipeline.resources import migration_root

migration_names = tuple(
    item.name
    for item in sorted(migration_root().iterdir(), key=lambda item: item.name)
    if item.is_file() and item.name.startswith("V")
)
display(migration_names)
```

Point ERD users to the maintained Mermaid diagrams and the schema-rendering command, which generates an ignored output on demand; do not commit generated runnable SQL.
Remove the conceptual-copy assertions at the end of `tests/test_migrations.py`; retain their schema/view coverage against the canonical migration resources and rendered output instead.

- [ ] **Step 6: Run notebook, Compose, documentation, and confidentiality checks**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/test_no_docker_runtime.py tests/test_pricing_model_notebooks.py \
  tests/test_scaffold_pricing_model.py tests/test_tutorials.py \
  tests/test_readme_contract.py tests/test_repo_hygiene.py -q
git check-ignore state pricing_models/mtpl_frequency/.local
```

Expected: all tests pass; tracked notebooks remain valid JSON with no outputs/attachments/widgets; confidential/generated directories remain ignored.

- [ ] **Step 7: Commit the development compatibility unit**

```bash
git add docker-compose.yml airflow/Dockerfile requirements.txt scripts/scaffold_pricing_model.py \
  pricing_models README.md docs tutorials tests
git commit -m "Align development workflows with installed package"
```

---

### Task 5: Validate wheel and sdist contents byte-for-byte

**Files:**
- Create: `tests/packaging/conftest.py`
- Create: `tests/packaging/test_distribution_contents.py`
- Modify: `pyproject.toml`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: complete `src/pricing_pipeline` tree and packaged resources.
- Produces: pytest fixtures `sdist_path: Path` and `wheel_path: Path` built once per packaging session; archive contract preventing accidental model/runtime leakage.

- [ ] **Step 1: Add a session fixture that builds the wheel from the sdist**

```python
# tests/packaging/conftest.py
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.2.0"


@pytest.fixture(scope="session")
def distribution_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("distribution")
    subprocess.run(
        [
            "uv", "build", "--force-pep517", "--sdist", "--clear",
            "--no-create-gitignore", "--out-dir", str(output), str(ROOT),
        ],
        check=True,
    )
    sdist = output / f"airflow_superglm_builder-{VERSION}.tar.gz"
    subprocess.run(
        [
            "uv", "build", "--force-pep517", "--wheel",
            "--no-create-gitignore", "--out-dir", str(output), str(sdist),
        ],
        check=True,
    )
    return output


@pytest.fixture(scope="session")
def sdist_path(distribution_dir: Path) -> Path:
    return distribution_dir / f"airflow_superglm_builder-{VERSION}.tar.gz"


@pytest.fixture(scope="session")
def wheel_path(distribution_dir: Path) -> Path:
    return distribution_dir / f"airflow_superglm_builder-{VERSION}-py3-none-any.whl"
```

- [ ] **Step 2: Write failing archive membership and metadata tests**

`tests/packaging/test_distribution_contents.py` must implement these exact checks with `zipfile`, `tarfile`, `email.parser`, `base64.urlsafe_b64decode`, and `hashlib.sha256`:

```python
FORBIDDEN_WHEEL_PREFIXES = (
    "tests/", "scripts/", "pricing_models/", "state/", "docs/",
    "tutorials/", "airflow/", "db/", "work_runtime/",
)


def test_wheel_has_only_package_and_dist_info(wheel_path):
    with ZipFile(wheel_path) as archive:
        names = archive.namelist()
        assert names
        assert all(
            name.startswith("pricing_pipeline/")
            or name.startswith("airflow_superglm_builder-0.2.0.dist-info/")
            for name in names
        )
        assert not any(name.startswith(FORBIDDEN_WHEEL_PREFIXES) for name in names)
        assert len(names) == len(set(names)) == len({name.casefold() for name in names})
        assert all(not PurePosixPath(name).is_absolute() for name in names)
        assert all(".." not in PurePosixPath(name).parts for name in names)
```

Add separate tests that:

- compare every path returned by `git ls-files src/pricing_pipeline` to `pricing_pipeline/<relative path>` in the wheel byte-for-byte, rejecting caches and other untracked source-tree residue;
- assert all 38 migrations, four offline DDL files, and the scaffold resource package exist;
- parse `METADATA` and assert exact name/version/Python floor/base requirements/extras;
- parse `WHEEL` and assert `Root-Is-Purelib: true` and tag `py3-none-any`;
- parse every non-empty `RECORD` digest/size and recompute it from the archive member;
- assert the sdist has one `airflow_superglm_builder-0.2.0/` root containing `pyproject.toml`, `README.md`, `PKG-INFO`, and `src/pricing_pipeline/**`, without root `pricing_pipeline/`, `pricing_models/`, `state/`, `.venv/`, `dist/`, or built archives.

- [ ] **Step 3: Run archive tests and observe the first build/content failure**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/packaging/test_distribution_contents.py -q
```

Expected before final Hatch rules/resource moves: build or archive membership assertions fail.

- [ ] **Step 4: Tighten Hatch sdist/wheel selection**

Retain wheel `packages = ["src/pricing_pipeline"]`. Add explicit sdist selection sufficient to rebuild the wheel:

```toml
[tool.hatch.build.targets.sdist]
include = [
  "/src/pricing_pipeline",
  "/pyproject.toml",
  "/README.md",
]
exclude = [
  "/pricing_models",
  "/state",
  "/.venv",
  "/dist",
]
```

Do not `force-include` any repository model/runtime path. Fix archive failures by correcting package/resource selection, never by weakening forbidden-path assertions.
Add `dist/` to `.gitignore` so the explicit final build cannot be committed accidentally.

- [ ] **Step 5: Run package archive and resource tests**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/packaging/test_project_metadata.py \
  tests/packaging/test_distribution_contents.py \
  tests/test_packaged_resources.py -q
```

Expected: one sdist and one pure-Python wheel pass exact byte, metadata, and resource checks.

- [ ] **Step 6: Commit the archive contract**

```bash
git add .gitignore pyproject.toml tests/packaging
git commit -m "Verify package distribution contents"
```

---

### Task 6: Prove fresh wheel installation outside the checkout

**Files:**
- Create: `tests/packaging/clean_wheel_smoke.py`
- Create: `tests/packaging/test_clean_wheel_install.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `wheel_path` from Task 5.
- Produces: release-gating clean-room test proving no editable install, cwd, `PYTHONPATH`, or checkout resource dependency.

- [ ] **Step 1: Write the pure-Python smoke program**

```python
# tests/packaging/clean_wheel_smoke.py
from __future__ import annotations

import importlib.metadata
import json
import os
import sys
from pathlib import Path

import pricing_pipeline
from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.resources import migration_root, offline_sqlite_root


checkout = Path(os.environ["FORBIDDEN_CHECKOUT"]).resolve()
package_file = Path(pricing_pipeline.__file__).resolve()
assert checkout not in package_file.parents
assert pricing_pipeline.__version__ == importlib.metadata.version(
    "airflow-superglm-builder"
) == "0.2.0"
assert len(tuple(item for item in migration_root().iterdir() if item.name.startswith("V"))) == 38
assert tuple(sorted(item.name for item in offline_sqlite_root().iterdir() if item.is_file())) == (
    "mlops.sql", "pricing.sql", "pricing_stg.sql", "pricing_views.sql",
)
distribution = importlib.metadata.distribution("airflow-superglm-builder")
direct_url = distribution.read_text("direct_url.json")
if direct_url is not None:
    direct_url_payload = json.loads(direct_url)
    assert direct_url_payload.get("dir_info", {}).get("editable") is not True
    assert str(checkout) not in direct_url
assert all(checkout not in Path(entry).resolve().parents for entry in sys.path if entry)

root = Path(os.environ["SMOKE_DATABASE_ROOT"])
engine, _paths = open_offline_sqlite(root)
with engine.connect() as connection:
    assert connection.exec_driver_sql(
        "SELECT COUNT(*) FROM pricing.MODEL_MONITOR_VARIANT"
    ).scalar_one() == 4
    assert connection.exec_driver_sql(
        "SELECT COUNT(*) FROM pricing.V_CURRENT_DEPLOYED_RELATIVITY"
    ).scalar_one() == 0
```

- [ ] **Step 2: Write the isolated install test**

```python
# tests/packaging/test_clean_wheel_install.py
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


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
```

- [ ] **Step 3: Run the clean-wheel smoke**

Run:

```bash
uv run --locked --all-extras python -m pytest -p no:cacheprovider \
  tests/packaging/test_clean_wheel_install.py -q
```

Expected: the new venv installs the built wheel and dependencies, then SQLite initializes while cwd and all module/resource origins remain outside the checkout.

- [ ] **Step 4: Document the package-foundation developer commands**

Update the basic README installation/test section to:

```text
uv sync --locked --all-extras
uv run --locked --all-extras python -m pytest -p no:cacheprovider -q
uv build --force-pep517 --sdist --wheel --clear --out-dir dist
```

State that `uv run` uses the editable development install and only `tests/packaging/test_clean_wheel_install.py` proves the built wheel.

- [ ] **Step 5: Run final package-foundation gates**

Run, from a clean worktree except for this task's intended files:

```bash
uv lock --check
uv run --locked --all-extras ruff format --check src tests scripts
uv run --locked --all-extras ruff check src tests scripts
uv run --locked --all-extras python -m pytest -p no:cacheprovider -q
uv build --force-pep517 --sdist --wheel --clear --out-dir dist
git diff --check
git status --short
```

Expected: full suite passes; Ruff and whitespace checks pass; only ignored `dist/` artifacts remain outside the intended diff. Review the built wheel member list once manually before committing.

- [ ] **Step 6: Commit the clean-room proof**

```bash
git add README.md tests/packaging
git commit -m "Prove clean wheel installation"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Package layout, version authority, dependency extras, canonical SQL resources, checkout-independent imports, and clean wheel/sdist validation each map to Tasks 1–6.
- [x] **Deliberate deferral:** `resources/scaffold/` is reserved but contains no obsolete template payload; the approved standalone-scaffold plan will populate and golden-test it before delivery step 1 is declared wholly complete.
- [x] **Single authority:** Root `db/` and maintained documentation/tutorial SQL copies are absent after Task 4; runtime code reads only installed resources unless an explicit low-level temporary directory is supplied by a test.
- [x] **Type consistency:** `migration_root()`, `offline_sqlite_root()`, `scaffold_root()`, and `materialized_migration_dir()` use the same names in every task; `migration_files()` accepts `Path | Traversable | None` throughout.
- [x] **No import escape hatch:** pytest has no `pythonpath`, notebooks do not insert the repo, and the clean smoke removes `PYTHONPATH` and uses `-I`.
- [x] **No confidentiality expansion:** wheel/archive assertions reject model projects, runtime modules, state, environment files, and repository-only sources.
- [x] **Next slice boundary:** Public CLI/wrappers are planned separately after this foundation, using the packaged resource interfaces established here.
