# Installed Init and Scaffold CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an installed `pricing-pipeline` command that initializes a standalone model repository with one editable `pricing_model.toml`, then scaffolds the six-notebook workflow from packaged resources without requiring uv, SQL Server, Jupyter, or the framework checkout.

**Architecture:** Add one lazy `argparse` entry point shared by the console script and `python -m pricing_pipeline`. Keep project configuration as a strict, versioned public boundary; keep filesystem mutation in a small no-follow transaction layer; and keep every generated file as an exact allowlisted package resource. The old monorepo scaffold remains available for one compatibility release, while the installed command owns the new standalone layout.

**Tech Stack:** Python 3.14, uv, Hatchling, `argparse`, Pydantic v2, `tomllib`, `importlib.resources`, `importlib.metadata` entry points, Jupyter notebook JSON, pytest.

**Spec:** `docs/superpowers/specs/2026-08-27-init-scaffold-cli-amendment.md` (scoped amendment to `docs/superpowers/specs/2026-08-26-installable-pricing-pipeline-design.md`)

## Global Constraints

- Keep distribution name `airflow-superglm-builder`, import namespace `pricing_pipeline`, version `0.2.0`, and `requires-python = ">=3.14"`.
- The documented command is `pricing-pipeline`; `python -m pricing_pipeline` must use the exact same parser and handlers.
- `init` creates only `pricing_model.toml`; it never creates or modifies `pyproject.toml`, `uv.lock`, notebooks, SQL, Git files, or directories.
- `scaffold` requires the initialized TOML and creates the flat standalone tree. It never creates `pricing_models/`, copies framework source, or initializes Git.
- Python-only `init`, `scaffold`, local SQLite, and read-only use are valid without `uv.lock`. No command in this slice may pretend an unlocked environment is governed evidence.
- This slice contains no governed mutation command. The amendment's verified-lock refusal test belongs to the first publication/deployment supervisor plan; do not invent an inert "governed" command merely to satisfy that future acceptance test.
- This slice seeds `model_spec.py` and `groupings.toml` but does not implement the parent design's attested model-source loader, canonical TOML grouping compiler/exporter, or governed notebook supervisor. Preserve the existing verified Joblib grouping path in the seeded notebooks until those separately specified subsystems replace it.
- Keep `[notebook]`, `[sqlserver]`, and the other current extras for compatibility, but install and document the base framework only. The private runtime-provider distribution owns its driver/auth dependencies; the model repo adds `ipykernel` as a development dependency.
- Generated notebook names are exactly `01_data_ingestion.ipynb`, `02_model_exploration.ipynb`, `03_model_training.ipynb`, `04_model_editor.ipynb`, `05_manual_adjustment.ipynb`, and `06_model_deployment.ipynb`.
- Generated notebook JSON has no outputs, execution counts, widgets, attachments, or absolute checkout paths.
- `pricing_model.toml` stores a registered `runtime_provider` alias, never credentials, a write switch, or a governed arbitrary module import path.
- Managed writes reject symlink/reparse-point ancestors and leaves, use no-follow/no-clobber operations, and leave `scaffold_state = "draft"` until all other output is durable.
- Initial scaffold never overwrites customized files. An exact retry is a byte- and mtime-preserving no-op.
- Keep the existing `scripts/scaffold_pricing_model.py` behavior and its tests for one release; do not import repository scripts from installed code.
- Do not add or inspect confidential data, fitted artifacts, work runtime code, credentials, or secret-bearing examples.
- Use TDD for every task and make one focused commit after each task passes its review gate.

---

## File Structure

### Created

- `src/pricing_pipeline/cli.py` — shared lazy parser, error-to-exit-code boundary, and subcommand dispatch.
- `src/pricing_pipeline/__main__.py` — module-form entry point only.
- `src/pricing_pipeline/project_config.py` — strict version-2 TOML models, loading, root discovery, and state editing.
- `src/pricing_pipeline/scaffold/__init__.py` — supported standalone template constants and public command results.
- `src/pricing_pipeline/scaffold/filesystem.py` — directory-anchored safe writes, transaction journal, rollback, and recovery.
- `src/pricing_pipeline/scaffold/commands.py` — `init` and `scaffold` orchestration.
- `src/pricing_pipeline/infra/runtime_provider.py` — installed entry-point alias resolution for private runtime adapters.
- `src/pricing_pipeline/resources/scaffold/init/pricing_model.toml` — commented draft configuration template.
- `src/pricing_pipeline/resources/scaffold/runtime-provider.md` — installed copy of the private adapter contract.
- `src/pricing_pipeline/resources/scaffold/standalone-v1/manifest.json` — exact resource-to-output mapping.
- `src/pricing_pipeline/resources/scaffold/standalone-v1/README.md`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/gitignore.txt`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/env-example.txt`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/model_spec.py`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/groupings.toml`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/sql/model_data.sql`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/notebooks/01_data_ingestion.ipynb`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/notebooks/02_model_exploration.ipynb`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/notebooks/03_model_training.ipynb`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/notebooks/04_model_editor.ipynb`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/notebooks/05_manual_adjustment.ipynb`
- `src/pricing_pipeline/resources/scaffold/standalone-v1/notebooks/06_model_deployment.ipynb`
- `docs/runtime-provider.md` — private adapter/entry-point contract and dependency ownership.
- `tests/cli/test_entrypoint.py` — parser parity, lazy imports, output, and exit codes.
- `tests/scaffold/test_project_config.py` — strict TOML schema and root discovery.
- `tests/scaffold/test_init.py` — one-file/no-clobber initializer behavior.
- `tests/scaffold/test_filesystem.py` — no-follow transaction, rollback, and recovery.
- `tests/scaffold/test_standalone_scaffold.py` — golden tree, notebook sanitation, collisions, and idempotency.
- `tests/scaffold/test_runtime_provider.py` — alias resolution and ambiguity handling.

### Modified

- `pyproject.toml` — add the console-script entry point only; preserve dependency/extras contract.
- `src/pricing_pipeline/resources/__init__.py` — expose exact scaffold traversables.
- `src/pricing_pipeline/infra/runtime.py` — accept an already resolved runtime module without project-root path injection.
- `README.md` — lead with the installed standalone workflow and keep the old script under a compatibility heading.
- `docs/notebooks/README.md` — use `runtime_provider`, new numbering, and flat standalone paths.
- `pricing_scaffold.example.toml` — label as legacy monorepo-only configuration.
- `tests/packaging/test_project_metadata.py` — require the console script and unchanged optional dependency contract.
- `tests/packaging/test_distribution_contents.py` — exact allowlist for reviewed scaffold resources.
- `tests/packaging/clean_wheel_smoke.py` — exercise CLI help/init/scaffold outside the checkout.
- `tests/packaging/test_clean_wheel_install.py` — install and invoke both entry-point forms in a fresh venv.
- `tests/test_readme_contract.py` — new documented commands, dependency ownership, and compatibility wording.

### Deliberately Unchanged

- `scripts/scaffold_pricing_model.py` and `tests/test_scaffold_pricing_model.py` — existing nested/monorepo compatibility command.
- `src/pricing_pipeline/resources/migrations/**` and `offline_sqlite/**` — no schema change belongs to this slice.
- `uv.lock` and `requirements.txt` — no dependency is added or removed.

---

### Task 1: Add the shared installed CLI entry point

**Files:**
- Create: `src/pricing_pipeline/cli.py`
- Create: `src/pricing_pipeline/__main__.py`
- Modify: `pyproject.toml`
- Create: `tests/cli/test_entrypoint.py`
- Modify: `tests/packaging/test_project_metadata.py`

**Interfaces:**
- Consumes: no scaffold implementation; handlers are imported lazily by dotted function name.
- Produces: `pricing_pipeline.cli.main(argv: Sequence[str] | None = None) -> int`; console script `pricing-pipeline`; module entry point `python -m pricing_pipeline`.

- [ ] **Step 1: Write the failing metadata and parser-parity tests**

```python
# tests/cli/test_entrypoint.py
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
```

Add this exact metadata assertion:

```python
# tests/packaging/test_project_metadata.py
def test_console_script_has_one_parser_authority():
    project = _project()["project"]
    assert project["scripts"] == {"pricing-pipeline": "pricing_pipeline.cli:main"}
```

- [ ] **Step 2: Run the focused tests and record the RED result**

Run:

```bash
uv run python -m pytest -p no:cacheprovider \
  tests/cli/test_entrypoint.py \
  tests/packaging/test_project_metadata.py -q
```

Expected: collection fails because `pricing_pipeline.cli` does not exist and the project has no script entry.

- [ ] **Step 3: Implement one lazy parser and both launch forms**

Use this public shape; subcommand modules must not be imported while building help:

```python
# src/pricing_pipeline/cli.py
from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable, Sequence


class UserCommandError(Exception):
    """A sanitized analyst-actionable command failure."""


_HANDLERS = {
    "init": "pricing_pipeline.scaffold.commands:run_init",
    "scaffold": "pricing_pipeline.scaffold.commands:run_scaffold",
}


def _load_handler(spec: str) -> Callable[[argparse.Namespace], tuple[str, ...]]:
    module_name, function_name = spec.split(":", maxsplit=1)
    return getattr(importlib.import_module(module_name), function_name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pricing-pipeline")
    subcommands = parser.add_subparsers(dest="command")
    for name, help_text in (
        ("init", "create pricing_model.toml, then stop for review"),
        ("scaffold", "create the configured standalone notebook workflow"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--root", type=str, default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = list(argv) if argv is not None else None
    if arguments == ["--help"] or arguments == ["-h"]:
        parser.print_help()
        return 0
    namespace = parser.parse_args(arguments)
    if namespace.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        messages = _load_handler(_HANDLERS[namespace.command])(namespace)
    except UserCommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception:
        print("error: pricing-pipeline failed unexpectedly; rerun with your normal support logging", file=sys.stderr)
        return 1
    for message in messages:
        print(message)
    return 0
```

The implementation may use a small `ArgumentParser` subclass so parser errors return `2` rather than escaping as `SystemExit`, but both launch forms must retain identical output. `__main__.py` contains only:

```python
from pricing_pipeline.cli import main

raise SystemExit(main())
```

Add to `pyproject.toml` without changing dependencies or extras:

```toml
[project.scripts]
pricing-pipeline = "pricing_pipeline.cli:main"
```

- [ ] **Step 4: Verify parser behavior and lazy optional imports**

Run:

```bash
uv sync --locked
uv run pricing-pipeline --help
uv run python -m pricing_pipeline --help
uv run python -m pytest -p no:cacheprovider \
  tests/cli/test_entrypoint.py \
  tests/packaging/test_project_metadata.py -q
```

Expected: both help commands match and the focused suite passes.

- [ ] **Step 5: Commit the CLI boundary**

```bash
git add pyproject.toml src/pricing_pipeline/cli.py src/pricing_pipeline/__main__.py \
  tests/cli/test_entrypoint.py tests/packaging/test_project_metadata.py
git commit -m "Add installed pricing pipeline CLI"
```

---

### Task 2: Implement strict project configuration and one-file `init`

**Files:**
- Create: `src/pricing_pipeline/project_config.py`
- Create: `src/pricing_pipeline/scaffold/__init__.py`
- Create: `src/pricing_pipeline/scaffold/filesystem.py`
- Create: `src/pricing_pipeline/scaffold/commands.py`
- Create: `src/pricing_pipeline/infra/runtime_provider.py`
- Modify: `src/pricing_pipeline/infra/runtime.py`
- Modify: `src/pricing_pipeline/notebook.py`
- Create: `src/pricing_pipeline/resources/scaffold/init/pricing_model.toml`
- Modify: `src/pricing_pipeline/resources/__init__.py`
- Create: `tests/scaffold/test_project_config.py`
- Create: `tests/scaffold/test_init.py`
- Create: `tests/scaffold/test_runtime_provider.py`
- Modify: `tests/test_notebook_database_targets.py`

**Interfaces:**
- Consumes: `pricing_pipeline.cli.UserCommandError`; `pricing_pipeline.resources.scaffold_root()`.
- Produces: `ProjectConfig`, `load_project_config(root, *, required_state=None)`, `inspect_initialized_config(source)`, `find_model_root(start)`, `render_scaffold_state(source, expected, replacement)`, `open_validated_root(root)`, `create_file_no_clobber(root_handle, relative_path, contents)`, `resolve_runtime_provider(alias, *, model_root)`, `runtime_from_provider(alias, *, model_root, env=None)`, `InitResult`, and `run_init(namespace) -> tuple[str, ...]`.

- [ ] **Step 1: Write RED tests for the full strict schema**

Cover all four validation variants and every fail-closed boundary. The core fixture should be:

```python
# tests/scaffold/test_project_config.py
VALID = {
    "schema_version": 2,
    "template_version": "standalone-v1",
    "scaffold_state": "draft",
    "model": {
        "name": "CLAIM_FREQUENCY",
        "label": "Claim frequency",
        "target": "claim_count",
        "model_type": "superglm_poisson",
        "problem_type": "frequency",
        "deployment_slot": "CLAIM_FREQUENCY_UAT",
        "features": ["driver_age", "vehicle_band", "region"],
        "dataset_name": "claim_frequency_model_frame",
        "source_system": "pricing_warehouse",
        "primary_keys": ["policy_period_id"],
        "fit_mode": "fit_reml",
        "scoring": ["deviance", "nll", "gini"],
    },
    "source": {
        "sql": "sql/model_data.sql",
        "data_as_of_column": "data_as_of",
        "support_files": [],
    },
    "roles": {"sample_weight_column": "exposure", "export_weight_column": "exposure"},
    "validation": {
        "kind": "kfold",
        "n_splits": 5,
        "shuffle": True,
        "random_state": 42,
        "materialize": False,
    },
    "notebook_defaults": {
        "database_mode": "local",
        "runtime_provider": "work-default",
        "expected_remote_database": "",
    },
    "manual_edit_defaults": {"source_selector": "deployed", "carry_forward": True},
}


def test_unknown_keys_and_reserved_placeholders_fail_closed(tmp_path):
    payload = copy.deepcopy(VALID)
    payload["model"]["features"] = ["<EDIT_ME>"]
    payload["unexpected"] = {"key": "value"}
    _write_toml(tmp_path / "pricing_model.toml", payload)
    with pytest.raises(ProjectConfigError) as error:
        load_project_config(tmp_path)
    message = str(error.value)
    assert "model.features" in message
    assert "unexpected" in message
    assert "value" not in message
```

Add parameterized cases for:

- exact root versions/state;
- stripped non-empty strings, unique ordered features/keys/scoring/support files;
- allowed metric IDs and problem/fit/model-state enums;
- target/features/key conflicts;
- local versus remote database requirements and alias syntax `^[a-z][a-z0-9-]*$`;
- lexical root-relative source/support paths with no `..`, absolute paths, or symlinks;
- `kfold`, `train_test_split`, `column_kfold`, and typed `column_holdout` field sets exactly as the spec defines;
- validation columns present in the declared frame-column union;
- `find_model_root()` finding exactly one marker and refusing ambiguity.

- [ ] **Step 2: Write RED tests for exact `init` mutation and output**

```python
# tests/scaffold/test_init.py
def test_init_creates_only_the_config_and_prints_next_action(tmp_path, capsys):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='model'\nversion='0'\n")
    result = cli.main(["init", "--root", str(tmp_path)])
    assert result == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "pricing_model.toml",
        "pyproject.toml",
    ]
    source = (tmp_path / "pricing_model.toml").read_bytes()
    assert b'scaffold_state = "draft"' in source
    output = capsys.readouterr().out
    assert str((tmp_path / "pricing_model.toml").resolve()) in output
    assert "pricing-pipeline scaffold" in output
```

Also prove: missing/non-file/symlink `pyproject.toml` fails with code `2`; existing valid config is byte/mtime preserving; malformed TOML, existing directory, leaf symlink, parent symlink, and a concurrent `O_EXCL` winner fail without overwrite; no `--force` flag exists; no `uv.lock` is required.

Add `tests/scaffold/test_runtime_provider.py` with a fake installed entry-point set. It proves one `work-default = "company_pricing_runtime.database"` entry resolves, while missing/duplicate aliases, entry-point attributes, invalid module names, and editable/distribution paths under the model root fail without importing model-controlled code.

```python
def test_registered_alias_returns_installed_module_name(monkeypatch, tmp_path):
    entry = FakeEntryPoint(
        name="work-default",
        group="pricing_pipeline.runtime_providers",
        value="company_pricing_runtime.database",
        dist=FakeDistribution(tmp_path / "installed-site-packages"),
    )
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda: FakeEntries([entry]))
    assert resolve_runtime_provider("work-default", model_root=tmp_path / "model").__name__ == (
        "company_pricing_runtime.database"
    )


@pytest.mark.parametrize("entries", [[], [ENTRY, ENTRY]], ids=("missing", "ambiguous"))
def test_missing_or_ambiguous_alias_fails_closed(monkeypatch, entries, tmp_path):
    monkeypatch.setattr(importlib.metadata, "entry_points", lambda: FakeEntries(entries))
    with pytest.raises(RuntimeProviderError, match="work-default"):
        resolve_runtime_provider("work-default", model_root=tmp_path)
```

- [ ] **Step 3: Run the config/init tests and record the RED result**

Run:

```bash
uv run python -m pytest -p no:cacheprovider \
  tests/scaffold/test_project_config.py \
  tests/scaffold/test_init.py \
  tests/scaffold/test_runtime_provider.py -q
```

Expected: collection fails on the absent modules and resources.

- [ ] **Step 4: Implement strict Pydantic version-2 models**

Use frozen, strict, extra-forbid models and a discriminated union:

```python
# src/pricing_pipeline/project_config.py
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
RelativePathText = NonEmpty


class StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class KFoldConfig(StrictConfig):
    kind: Literal["kfold"]
    n_splits: int = Field(ge=2)
    shuffle: bool = True
    random_state: int | None = 42
    materialize: bool = False


class TrainTestSplitConfig(StrictConfig):
    kind: Literal["train_test_split"]
    test_size: float = Field(gt=0, lt=1, allow_inf_nan=False)
    shuffle: bool = True
    random_state: int | None = 42
    stratify_column: NonEmpty | None = None
    materialize: bool = False


class ColumnKFoldConfig(StrictConfig):
    kind: Literal["column_kfold"]
    column: NonEmpty
    materialize: bool = False


class ColumnHoldoutConfig(StrictConfig):
    kind: Literal["column_holdout"]
    column: NonEmpty
    train_values: tuple[str | int | float | bool, ...]
    test_values: tuple[str | int | float | bool, ...]
    materialize: bool = False


ValidationConfig = Annotated[
    KFoldConfig | TrainTestSplitConfig | ColumnKFoldConfig | ColumnHoldoutConfig,
    Field(discriminator="kind"),
]
```

Define `ModelConfig`, `SourceConfig`, `RolesConfig`, `NotebookDefaults`, `ManualEditDefaults`, and:

```python
class ProjectConfig(StrictConfig):
    schema_version: Literal[2]
    template_version: Literal["standalone-v1"]
    scaffold_state: Literal["draft", "current", "manual_pending"]
    model: ModelConfig
    source: SourceConfig
    roles: RolesConfig = Field(default_factory=RolesConfig)
    validation: ValidationConfig
    notebook_defaults: NotebookDefaults = NotebookDefaults()
    manual_edit_defaults: ManualEditDefaults = ManualEditDefaults()
```

The model-level validator accumulates paths of every reserved `"<EDIT_ME>"`, validates uniqueness/relationships without echoing values, and validates source paths relative to the already resolved model root. TOML arrays are explicitly checked then converted to immutable tuples in `mode="before"` validators so strict validation does not retain mutable lists. Column-holdout values accept exact string, integer excluding bool, boolean, finite float, local date, local datetime, and offset datetime values.

`load_project_config()` uses `tomllib.load`, converts Pydantic errors to stable dotted-field messages, and checks `required_state` when supplied. It permits the managed `sql/model_data.sql` path to be absent only while state is `draft`; every other declared support file must already be a contained regular non-symlink file. `inspect_initialized_config()` is the deliberately narrower idempotent-init check: it requires syntactically valid TOML plus supported root version/template/state but permits the reserved draft sentinels. `render_scaffold_state()` replaces the one root-level state assignment after parsed-state verification and preserves every unrelated byte/comment.

- [ ] **Step 5: Add the static init template and exact resource accessor**

The template contains this complete set of active fields; optional role examples remain comments:

```toml
schema_version = 2
template_version = "standalone-v1"
scaffold_state = "draft"

[model]
name = "<EDIT_ME>"
label = "<EDIT_ME>"
target = "<EDIT_ME>"
model_type = "<EDIT_ME>"
problem_type = "<EDIT_ME>"
deployment_slot = "<EDIT_ME>"
features = ["<EDIT_ME>"]
dataset_name = "<EDIT_ME>"
source_system = "<EDIT_ME>"
primary_keys = ["<EDIT_ME>"]
fit_mode = "fit_reml"
scoring = ["deviance", "nll", "gini"]

[source]
sql = "sql/model_data.sql"
data_as_of_column = "data_as_of"
support_files = []

[roles]
# sample_weight_column = "exposure"
# export_weight_column = "exposure"
# offset_column = "log_exposure"
# offset_source_column = "exposure"
# offset_label = "log(exposure)"

[validation]
kind = "kfold"
n_splits = 5
shuffle = true
random_state = 42
materialize = false

[notebook_defaults]
database_mode = "local"
# This is an installed entry-point alias, not a Python module path.
# See docs/runtime-provider.md in the framework repository or the packaged
# pricing_pipeline.resources.runtime_provider_doc() page.
runtime_provider = "<EDIT_ME>"
expected_remote_database = ""

[manual_edit_defaults]
source_selector = "deployed"
carry_forward = true
```

Add `init_template() -> Traversable` beside `scaffold_root()` in `resources/__init__.py`.

- [ ] **Step 6: Implement root-anchored creation and `run_init`**

`open_validated_root()` walks every path component without following links, opens the final directory with `O_DIRECTORY | O_NOFOLLOW`, and validates `pyproject.toml` relative to that trusted handle as a regular non-symlink file. `create_file_no_clobber()` accepts one lexical relative child name, uses `os.open(..., dir_fd=root_fd, O_CREAT | O_EXCL | O_WRONLY | O_NOFOLLOW, 0o644)`, writes/fsyncs, and fsyncs the directory. Platforms without the required primitives raise a sanitized unsupported-platform error before mutation.

`run_init()` uses those primitives to install the packaged template. A `FileExistsError` triggers no-follow read-only `inspect_initialized_config()`: a syntactically valid supported config returns the idempotent message even when its draft sentinels remain; every other existing entry raises `UserCommandError`. Its returned messages name the absolute file, the sentinel fields, and the exact next command. No persistent lock or temporary file is created, so the final directory contains only its pre-existing `pyproject.toml` and the new config.

- [ ] **Step 7: Implement the installed runtime-provider alias boundary**

Private runtime packages register a module-only entry point:

```toml
[project.entry-points."pricing_pipeline.runtime_providers"]
work-default = "company_pricing_runtime.database"
```

`resolve_runtime_provider(alias: str, *, model_root: Path) -> ModuleType` validates `^[a-z][a-z0-9-]*$`, selects exactly one installed entry point, rejects `module:attribute` values, verifies the owning distribution is not editable from or located beneath `model_root`, and loads that exact installed entry point without consulting cwd. `runtime_from_provider()` converts that module through a new shared `runtime_from_module_object()` helper in `infra/runtime.py`.

Preserve legacy `runtime_from_module()` and its project-root path behavior for the existing monorepo scaffold during the compatibility release. Extend `notebook.connect()` with mutually exclusive `runtime_provider` and `model_root` keywords; remote provider mode calls `runtime_from_provider()`, while existing `runtime_module` callers remain unchanged. Add focused database-target tests proving local mode never resolves a provider, remote mode resolves the alias, and specifying both boundaries fails.

- [ ] **Step 8: Run the focused config/init/runtime suite**

Run:

```bash
uv run python -m pytest -p no:cacheprovider \
  tests/scaffold/test_project_config.py \
  tests/scaffold/test_init.py \
  tests/scaffold/test_runtime_provider.py \
  tests/test_runtime_contract.py \
  tests/test_notebook_database_targets.py \
  tests/cli/test_entrypoint.py -q
uv run ruff check src/pricing_pipeline/project_config.py \
  src/pricing_pipeline/scaffold src/pricing_pipeline/infra/runtime_provider.py \
  src/pricing_pipeline/infra/runtime.py src/pricing_pipeline/notebook.py \
  tests/scaffold tests/cli/test_entrypoint.py
uv run ruff format --check src/pricing_pipeline/project_config.py \
  src/pricing_pipeline/scaffold src/pricing_pipeline/infra/runtime_provider.py \
  src/pricing_pipeline/infra/runtime.py src/pricing_pipeline/notebook.py \
  tests/scaffold tests/cli/test_entrypoint.py
```

Expected: all tests and both Ruff commands pass.

- [ ] **Step 9: Commit the config, initializer, and provider resolver**

```bash
git add src/pricing_pipeline/project_config.py src/pricing_pipeline/scaffold \
  src/pricing_pipeline/infra/runtime_provider.py src/pricing_pipeline/infra/runtime.py \
  src/pricing_pipeline/notebook.py \
  src/pricing_pipeline/resources/__init__.py \
  src/pricing_pipeline/resources/scaffold/init/pricing_model.toml \
  tests/scaffold/test_project_config.py tests/scaffold/test_init.py \
  tests/scaffold/test_runtime_provider.py tests/test_notebook_database_targets.py
git commit -m "Add standalone model project initialization"
```

---

### Task 3: Add the safe multi-file scaffold transaction

**Files:**
- Modify: `src/pricing_pipeline/scaffold/filesystem.py`
- Create: `tests/scaffold/test_filesystem.py`

**Interfaces:**
- Consumes: Task 2's directory-anchored `open_validated_root()` and `create_file_no_clobber()` primitives plus immutable `PlannedFile` values.
- Produces: `PlannedFile(relative_path: PurePosixPath, contents: bytes)`, `ScaffoldTransaction(root, files, config_before, config_after)`, `apply()`, `recover()`, and `ScaffoldCollisionError`.

- [ ] **Step 1: Write RED transaction tests with fault injection**

Use a three-file fixture plus the draft/current config transition:

```python
# tests/scaffold/test_filesystem.py
def test_handled_failure_removes_new_files_and_preserves_draft(tmp_path, monkeypatch):
    root = initialized_root(tmp_path)
    transaction = ScaffoldTransaction(
        root=root,
        files=(
            PlannedFile(PurePosixPath("README.md"), b"readme\n"),
            PlannedFile(PurePosixPath("sql/model_data.sql"), b"SELECT 1;\n"),
        ),
        config_before=(root / "pricing_model.toml").read_bytes(),
        config_after=render_scaffold_state(
            (root / "pricing_model.toml").read_bytes(), "draft", "current"
        ),
    )
    monkeypatch.setattr(transaction, "_install", fail_on_second_install(transaction._install))
    with pytest.raises(OSError, match="injected write failure"):
        transaction.apply()
    assert not (root / "README.md").exists()
    assert not (root / "sql").exists()
    assert load_project_config(root).scaffold_state == "draft"
    assert not transaction.journal_path.exists()
```

Add tests for: complete preflight before mutation; duplicate/casefold-colliding/absolute/`..` paths; root, ancestor, and leaf symlinks; concurrent root lock; destination appearing after preflight; identical existing files accepted without mtime change; different existing bytes rejected; handled failures before/after every install; crash journal blocking ordinary apply; `recover-old` restoring draft and removing new files; `recover-new` verifying hashes and completing current; external modification causing recovery refusal; temporary/journal cleanup; directory fsync calls; unsupported `O_NOFOLLOW`/directory handles failing closed.

- [ ] **Step 2: Run the focused test and capture RED**

Run:

```bash
uv run python -m pytest -p no:cacheprovider tests/scaffold/test_filesystem.py -q
```

Expected: collection fails because the transaction module is absent.

- [ ] **Step 3: Implement immutable planning and preflight**

Use these exact value objects:

```python
@dataclass(frozen=True)
class PlannedFile:
    relative_path: PurePosixPath
    contents: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.contents).hexdigest()


@dataclass(frozen=True)
class JournalEntry:
    relative_path: str
    sha256: str
    installed: bool
```

Open the validated root once with `O_RDONLY | O_DIRECTORY | O_NOFOLLOW`, hold an exclusive advisory lock on that descriptor for the whole transaction, and perform traversal relative to directory descriptors. Reject casefold duplicates before touching disk. For each managed path, reject symlink/reparse points and accept an existing regular file only when its bytes exactly equal the plan. Capture its device/inode/file identity under the lock.

- [ ] **Step 4: Implement no-clobber staging, journal, rollback, and recovery**

For each new file, create a random same-directory temporary with `O_CREAT | O_EXCL | O_NOFOLLOW`, write/fsync it, then install without replacement using a hard-link-at/no-follow operation and unlink the temporary. Create parent directories one component at a time relative to trusted directory handles. Write a canonical JSON journal containing schema version, root identity, config old/new hashes, and each planned path/hash/install bit; fsync it and its parent before the first install.

Keep `pricing_model.toml` draft until every other file is installed and durable. Revalidate the captured config identity/bytes, atomically replace it with the current-state bytes, fsync it/root, mark the journal complete, then delete the journal. A caught failure rolls back only files created by this transaction and restores/removes newly created empty directories. A process-level crash leaves the journal; the next command refuses normal work and accepts only exact hash-verified old/new recovery.

Use one fixed journal name, `.pricing-pipeline-scaffold.json`, and fixed temporary prefix `.pricing-pipeline-tmp-`; add both to the generated Git ignore template later. Do not persist lock files.

- [ ] **Step 5: Verify the transaction suite and filesystem hygiene**

Run:

```bash
uv run python -m pytest -p no:cacheprovider tests/scaffold/test_filesystem.py -q
uv run ruff check src/pricing_pipeline/scaffold/filesystem.py tests/scaffold/test_filesystem.py
uv run ruff format --check src/pricing_pipeline/scaffold/filesystem.py \
  tests/scaffold/test_filesystem.py
git diff --check
```

Expected: all commands pass.

- [ ] **Step 6: Commit the transaction layer**

```bash
git add src/pricing_pipeline/scaffold/filesystem.py \
  tests/scaffold/test_filesystem.py
git commit -m "Add atomic standalone scaffold transaction"
```

---

### Task 4: Package and render the standalone six-notebook workflow

**Files:**
- Create: all `src/pricing_pipeline/resources/scaffold/standalone-v1/**` files listed above.
- Modify: `src/pricing_pipeline/cli.py`
- Modify: `src/pricing_pipeline/scaffold/commands.py`
- Modify: `src/pricing_pipeline/scaffold/__init__.py`
- Modify: `src/pricing_pipeline/resources/__init__.py`
- Create: `tests/scaffold/test_standalone_scaffold.py`
- Modify: `tests/packaging/test_distribution_contents.py`

**Interfaces:**
- Consumes: `load_project_config()`, `render_scaffold_state()`, `ScaffoldTransaction`, and `scaffold_root()`.
- Produces: `ScaffoldResult(root: Path, created_files: tuple[Path, ...], reused_files: tuple[Path, ...])`; `run_scaffold(namespace) -> tuple[str, ...]`; exact `standalone-v1` project bytes.

- [ ] **Step 1: Write the RED golden-tree and behavior tests**

```python
# tests/scaffold/test_standalone_scaffold.py
EXPECTED_FILES = {
    "pyproject.toml",
    "pricing_model.toml",
    "README.md",
    ".gitignore",
    ".env.example",
    "model_spec.py",
    "groupings.toml",
    "sql/model_data.sql",
    "01_data_ingestion.ipynb",
    "02_model_exploration.ipynb",
    "03_model_training.ipynb",
    "04_model_editor.ipynb",
    "05_manual_adjustment.ipynb",
    "06_model_deployment.ipynb",
}


def test_scaffold_creates_exact_flat_tree_and_marks_current(configured_root):
    assert cli.main(["scaffold", "--root", str(configured_root)]) == 0
    actual = {
        path.relative_to(configured_root).as_posix()
        for path in configured_root.rglob("*")
        if path.is_file()
    }
    assert actual == EXPECTED_FILES
    assert load_project_config(configured_root).scaffold_state == "current"
    assert not (configured_root / "pricing_models").exists()
    assert not (configured_root / "pricing_pipeline").exists()
```

Add tests proving: missing config returns code `2` and says `pricing-pipeline init`; every remaining sentinel appears as a dotted field error; no writes occur before full validation; remote mode requires expected database; initial support-file/source collisions are handled exactly; a conflict in any managed output causes zero mutation; successful retry preserves bytes and nanosecond mtimes; a current project preserves customized analyst files byte-for-byte while rejecting missing, non-regular, symlinked, or structurally invalid required roles; handled transaction failure stays draft; crash/recovery behavior is exposed with `scaffold --recover-old|--recover-new` only; no lockfile is required.

Notebook tests must load every JSON document and assert: `nbformat == 4`; code compiles; code outputs are empty; execution counts are `None`; metadata has no widgets; cells have no attachments; absolute checkout/worktree paths, `sys.path.insert`, `ALLOW_REMOTE_WRITES`, configured dotted runtime-module literals, and direct runtime imports from the model root are absent. Remote connectivity uses only the configured provider alias through `connect()`.

- [ ] **Step 2: Run the scaffold test and capture RED**

Run:

```bash
uv run python -m pytest -p no:cacheprovider \
  tests/scaffold/test_standalone_scaffold.py -q
```

Expected: failures for absent resources and unimplemented `run_scaffold`.

- [ ] **Step 3: Create an exact resource manifest and safe output mapping**

`manifest.json` has one version and an ordered seed-once mapping; packaged resource names avoid secret-path false positives while output names stay conventional:

```json
{
  "template_version": "standalone-v1",
  "files": [
    {"resource": "README.md", "output": "README.md", "policy": "seed_once"},
    {"resource": "gitignore.txt", "output": ".gitignore", "policy": "seed_once"},
    {"resource": "env-example.txt", "output": ".env.example", "policy": "seed_once"},
    {"resource": "model_spec.py", "output": "model_spec.py", "policy": "seed_once"},
    {"resource": "groupings.toml", "output": "groupings.toml", "policy": "seed_once"},
    {"resource": "sql/model_data.sql", "output": "sql/model_data.sql", "policy": "seed_once"},
    {"resource": "notebooks/01_data_ingestion.ipynb", "output": "01_data_ingestion.ipynb", "policy": "seed_once"},
    {"resource": "notebooks/02_model_exploration.ipynb", "output": "02_model_exploration.ipynb", "policy": "seed_once"},
    {"resource": "notebooks/03_model_training.ipynb", "output": "03_model_training.ipynb", "policy": "seed_once"},
    {"resource": "notebooks/04_model_editor.ipynb", "output": "04_model_editor.ipynb", "policy": "seed_once"},
    {"resource": "notebooks/05_manual_adjustment.ipynb", "output": "05_manual_adjustment.ipynb", "policy": "seed_once"},
    {"resource": "notebooks/06_model_deployment.ipynb", "output": "06_model_deployment.ipynb", "policy": "seed_once"}
  ]
}
```

The implementation validates this manifest against a Python constant and SHA-256s all resource bytes before planning. `tests/packaging/test_distribution_contents.py` enumerates every one of these resources exactly; unknown scaffold files still fail the archive confidentiality gate.

- [ ] **Step 4: Build static, config-driven notebook resources**

The generated `.gitignore` contains at least:

```gitignore
.local/
state/
data/
artifacts/
secrets/
.env
*.parquet
*.joblib
*.pkl
*.pickle
*.npz
.pricing-pipeline-scaffold.json
**/.pricing-pipeline-tmp-*
```

The SQL seed is deliberately company-neutral and cannot accidentally return data before review:

```sql
-- Replace this file with the reviewed model-frame query.
-- Bind the configured data-as-at value and finish with deterministic primary-key ordering.
SELECT 1 AS replace_with_primary_key
WHERE 1 = 0
ORDER BY replace_with_primary_key;
```

Port the already-tested workflow cells using this exact role mapping:

```text
current 01_data_ingestion.ipynb     -> standalone 01_data_ingestion.ipynb
current 99_scratch_work.ipynb       -> standalone 02_model_exploration.ipynb
current 02_model_training.ipynb     -> standalone 03_model_training.ipynb
current 03_model_editor.ipynb       -> standalone 04_model_editor.ipynb
current 04_manual_adjustment.ipynb  -> standalone 05_manual_adjustment.ipynb
current 05_model_deployment.ipynb   -> standalone 06_model_deployment.ipynb
```

Replace the legacy parent search/embedded values in every notebook with this managed setup cell:

```python
from pathlib import Path

from pricing_pipeline.project_config import find_model_root, load_project_config

PROJECT_ROOT = find_model_root(Path.cwd())
CONFIG = load_project_config(PROJECT_ROOT, required_state="current")
LOCAL_ROOT = PROJECT_ROOT / ".local"
SQL_PATH = PROJECT_ROOT / CONFIG.source.sql
```

Every connection cell calls `connect(mode=CONFIG.notebook_defaults.database_mode, runtime_provider=CONFIG.notebook_defaults.runtime_provider, model_root=PROJECT_ROOT, local_root=LOCAL_ROOT, expected_remote_database=CONFIG.notebook_defaults.expected_remote_database)` and omits the legacy `runtime_module` and remote-write-switch arguments. The ingestion notebook reads SQL with `SQL_PATH.read_text(encoding="utf-8")`; the exploration notebook is explicitly non-publishing and reuses the same source/frame paths; training imports `build_raw_features` and `build_model` from root `model_spec.py`; editor/manual/deployment derive model name/label/slot/defaults from `CONFIG`. Preserve existing calls for frame manifests, data-as-at, grouping artifacts, raw/routine candidates, editor sessions, manual policies, and deployment. Replace only location/config plumbing, not governed model behavior. The canonical tracked-TOML grouping compiler/exporter remains a separate parent-spec subsystem; this slice does not mislabel the existing verified Joblib handoff as that compiler.

`model_spec.py` is the one tracked analyst-owned model-definition module. It loads the root config without mutating `sys.path` and provides the parent design's exact callables:

```python
from pathlib import Path

from superglm import Categorical, SuperGLM, Tweedie

from pricing_pipeline.project_config import load_project_config

CONFIG = load_project_config(Path(__file__).resolve().parent, required_state="current")


def build_raw_features() -> dict[str, object]:
    return {name: Categorical() for name in CONFIG.model.features}


def build_model(*, features: dict[str, object] | None = None) -> SuperGLM:
    families = {
        "frequency": "poisson",
        "severity": "gamma",
        "burn_cost": Tweedie(p=1.5),
    }
    return SuperGLM(
        features=build_raw_features() if features is None else features,
        family=families[CONFIG.model.problem_type],
        selection_penalty=0.0,
    )
```

The file tells the analyst to replace default categorical specs with the intended Numeric, OrderedCategorical, spline, monotonic, and interaction definitions before governed training. Tests require a fresh feature mapping per call, exact configured key order, and preservation of an explicitly supplied mapping. `groupings.toml` is valid empty TOML (`format_version = 1` and an empty `[features]` table) with commented examples for multiple per-feature groups and typed levels; it stores no pickle/joblib object.

- [ ] **Step 5: Implement `run_scaffold` as validate → render → transact**

The command validates the config in `draft` or `current`, resolves every resource and root-relative support path, builds immutable `PlannedFile` values, changes only the root state line in `config_after`, and delegates initial mutation to `ScaffoldTransaction`. In `draft`, every seed destination must be absent or byte-identical before any write. In `current`, scaffold performs read-only role validation and returns without writing: customized regular model source, SQL, grouping config, README/Git files, and sanitized notebook source are preserved; missing/wrong-kind/symlinked roles fail. Add mutually exclusive recovery actions to the scaffold parser:

```text
pricing-pipeline scaffold --root PATH --recover-old
pricing-pipeline scaffold --root PATH --recover-new
```

Normal user-facing success prints absolute created paths and ends with:

```text
Scaffold ready. Next: add ipykernel to this model repo with `uv add --dev ipykernel`, then open 01_data_ingestion.ipynb.
```

- [ ] **Step 6: Verify the standalone scaffold, existing scaffold compatibility, and package inventory**

Run:

```bash
uv run python -m pytest -p no:cacheprovider \
  tests/scaffold/test_standalone_scaffold.py \
  tests/scaffold/test_filesystem.py \
  tests/test_scaffold_pricing_model.py \
  tests/packaging/test_distribution_contents.py -q
uv run ruff check src/pricing_pipeline/scaffold tests/scaffold
uv run ruff format --check src/pricing_pipeline/scaffold tests/scaffold
git diff --check
```

Expected: all commands pass; the old nested scaffold tests remain unchanged and green.

- [ ] **Step 7: Commit the standalone scaffold**

```bash
git add src/pricing_pipeline/cli.py src/pricing_pipeline/resources \
  src/pricing_pipeline/scaffold \
  tests/scaffold/test_standalone_scaffold.py \
  tests/packaging/test_distribution_contents.py
git commit -m "Add standalone notebook project scaffold"
```

---

### Task 5: Document the standalone install and private runtime-provider contract

**Files:**
- Create: `src/pricing_pipeline/resources/scaffold/runtime-provider.md`
- Modify: `src/pricing_pipeline/resources/__init__.py`
- Create: `docs/runtime-provider.md`
- Modify: `README.md`
- Modify: `docs/notebooks/README.md`
- Modify: `pricing_scaffold.example.toml`
- Modify: `tests/test_readme_contract.py`
- Modify: `tests/packaging/test_distribution_contents.py`

**Interfaces:**
- Consumes: Task 2's installed entry-point alias resolver and the existing runtime adapter contract.
- Produces: `runtime_provider_doc() -> Traversable`; exact private-package registration and dependency-ownership documentation.

- [ ] **Step 1: Write RED documentation and packaged-page tests**

```python
# tests/test_readme_contract.py
def test_runtime_provider_page_is_packaged_without_drift():
    repository_page = (ROOT / "docs/runtime-provider.md").read_bytes()
    assert runtime_provider_doc().read_bytes() == repository_page


def test_quick_start_uses_base_install_then_init_and_scaffold():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    commands = (
        "uv init --bare --python 3.14",
        "uv add \"airflow-superglm-builder @ git+ssh://git@HOST/TEAM/REPOSITORY.git\" --tag v0.2.0",
        "uv run pricing-pipeline init",
        "uv run pricing-pipeline scaffold",
        "uv add --dev ipykernel",
        "python -m pricing_pipeline init",
        "python -m pricing_pipeline scaffold",
    )
    positions = [readme.index(command) for command in commands]
    assert positions[:5] == sorted(positions[:5])
```

Add assertions that the base workflow never shows `[notebook]`, `[sqlserver]`, `[azure]`, `pyodbc`, or `ipykernel` as framework install extras; prose must instead assign `ipykernel` to the model repo and driver/auth dependencies to the private runtime distribution. Assert the legacy script/config are clearly labeled compatibility-only.

- [ ] **Step 2: Run the focused tests and capture RED**

Run:

```bash
uv run python -m pytest -p no:cacheprovider \
  tests/test_readme_contract.py tests/packaging/test_distribution_contents.py -q
```

Expected: failures for the absent packaged page and stale README workflow.

- [ ] **Step 3: Rewrite the top-level usage docs around the installed flow**

README quick start must be exactly this shape:

```bash
uv init --bare --python 3.14
uv add "airflow-superglm-builder @ git+ssh://git@HOST/TEAM/REPOSITORY.git" --tag v0.2.0
uv run pricing-pipeline init
# edit pricing_model.toml
uv run pricing-pipeline scaffold
uv add --dev ipykernel
```

Follow it with the installed-package fallback:

```bash
python -m pricing_pipeline init
python -m pricing_pipeline scaffold
```

State plainly: base installation does not install `ipykernel`, `pyodbc`, or Azure packages; the model repo owns its kernel dependency; the private provider owns SQL/auth dependencies; no-uv local scaffolding is allowed; governed publish/deploy will require a verified `uv.lock` in its later command slice. Put the current root script under “Legacy monorepo scaffold” and mark `pricing_scaffold.example.toml` as applying only to that compatibility command.

`docs/runtime-provider.md` documents `get_engine(database=None)`, optional `get_schema_names()`, `get_runtime_settings()`/`get_settings()`, and `ensure_database(database)` plus this exact registration:

```toml
[project.entry-points."pricing_pipeline.runtime_providers"]
work-default = "company_pricing_runtime.database"
```

It states that credentials remain in the private package's secret provider and `pricing_model.toml` contains only the alias. Package the exact same bytes as `resources/scaffold/runtime-provider.md`, expose `runtime_provider_doc() -> Traversable`, and test byte equality so installed callers and repository readers cannot drift.

- [ ] **Step 4: Verify docs, resource inventory, and legacy compatibility**

Run:

```bash
uv run python -m pytest -p no:cacheprovider \
  tests/test_runtime_contract.py \
  tests/test_readme_contract.py \
  tests/packaging/test_distribution_contents.py \
  tests/test_scaffold_pricing_model.py -q
uv run ruff check src/pricing_pipeline/resources/__init__.py tests/test_readme_contract.py
uv run ruff format --check src/pricing_pipeline/resources/__init__.py \
  tests/test_readme_contract.py
git diff --check
```

Expected: all commands pass.

- [ ] **Step 5: Commit the installed workflow and runtime-provider docs**

```bash
git add src/pricing_pipeline/resources/__init__.py \
  src/pricing_pipeline/resources/scaffold/runtime-provider.md \
  docs/runtime-provider.md README.md docs/notebooks/README.md \
  pricing_scaffold.example.toml tests/test_readme_contract.py \
  tests/packaging/test_distribution_contents.py
git commit -m "Document installed model repository workflow"
```

---

### Task 6: Prove clean-wheel, no-extra, checkout-independent operation

**Files:**
- Modify: `tests/packaging/clean_wheel_smoke.py`
- Modify: `tests/packaging/test_clean_wheel_install.py`
- Modify: `tests/packaging/test_distribution_contents.py`
- Modify: `tests/packaging/test_project_metadata.py`

**Interfaces:**
- Consumes: the complete installed CLI, scaffold resources, and existing build fixtures.
- Produces: release evidence that both launch forms initialize/scaffold from the built wheel in an unrelated directory with no checkout import path or optional packages.

- [ ] **Step 1: Extend the clean-wheel smoke with the real standalone lifecycle**

In the isolated smoke program, create a temporary model root and only this unmanaged file:

```python
(model_root / "pyproject.toml").write_text(
    "[project]\nname = 'clean-wheel-model'\nversion = '0.0.0'\n",
    encoding="utf-8",
)
```

Call `pricing_pipeline.cli.main(["init", "--root", str(model_root)])`, replace each exact `"<EDIT_ME>"` field with the valid fixture values from Task 2, then call `main(["scaffold", "--root", str(model_root)])`. Assert exact tree, current state, sanitized notebook JSON, and idempotent bytes/mtimes. Use `importlib.metadata.distribution()` and require `PackageNotFoundError` for distributions `pyodbc`, `ipykernel`, `azure-identity`, and `azure-identity-broker`; do not install extras into the smoke venv.

- [ ] **Step 2: Add subprocess coverage for both installed launch forms**

`test_clean_wheel_install.py` invokes:

```python
[str(venv / "bin" / "pricing-pipeline"), "init", "--root", str(console_root)]
[str(python), "-I", "-m", "pricing_pipeline", "init", "--root", str(module_root)]
```

Then configure/scaffold both roots and assert identical managed bytes. Remove `PYTHONPATH`, use unrelated cwd, and retain the existing checkout-path rejection.

- [ ] **Step 3: Run the packaging tests and fix only true new failures**

Run:

```bash
uv run python -m pytest -p no:cacheprovider tests/packaging -q
uv run python -m pytest -p no:cacheprovider tests/scaffold tests/cli -q
uv build --force-pep517 --sdist --wheel --clear --out-dir dist
```

Expected: all tests pass; archive inspection proves the exact scaffold allowlist and console-script metadata; wheel and sdist build successfully.

- [ ] **Step 4: Run the full functional regression suite**

Run:

```bash
uv lock --check
uv run --locked --all-extras python -m pytest -p no:cacheprovider -q
git diff --check
```

Expected: full pytest exits `0`, the lock is unchanged/valid, and the diff check is clean. Record existing warning and repository-wide Ruff debt separately; do not hide a new regression behind baseline debt.

- [ ] **Step 5: Run touched-file lint and a confidentiality scan**

Run:

```bash
uv run ruff check \
  src/pricing_pipeline/cli.py src/pricing_pipeline/__main__.py \
  src/pricing_pipeline/project_config.py src/pricing_pipeline/scaffold \
  src/pricing_pipeline/infra/runtime_provider.py \
  tests/cli tests/scaffold tests/packaging
uv run ruff format --check \
  src/pricing_pipeline/cli.py src/pricing_pipeline/__main__.py \
  src/pricing_pipeline/project_config.py src/pricing_pipeline/scaffold \
  src/pricing_pipeline/infra/runtime_provider.py \
  tests/cli tests/scaffold tests/packaging
git grep -nEi '(password|client_secret|access_token|private[_ -]?key|confidential.*parquet)' -- \
  src/pricing_pipeline/resources/scaffold docs/runtime-provider.md README.md
```

Expected: Ruff passes for all new/touched code; the grep returns only explanatory generic prose, never a value, dataset name, artifact, or credential.

- [ ] **Step 6: Commit the clean-wheel proof**

```bash
git add tests/packaging/clean_wheel_smoke.py \
  tests/packaging/test_clean_wheel_install.py \
  tests/packaging/test_distribution_contents.py \
  tests/packaging/test_project_metadata.py
git commit -m "Prove installed init and scaffold workflow"
```

- [ ] **Step 7: Request final code review before branch integration**

Review the complete range from the Task 1 parent through Task 6 for:

- exact spec coverage and no scope creep;
- safe init/scaffold filesystem behavior;
- strict TOML and draft/current transitions;
- clean-wheel/checkout independence;
- optional dependency laziness;
- standalone versus legacy scaffold compatibility; and
- archive confidentiality/resource allowlisting.

Resolve every Critical or Important finding, rerun the affected focused suite plus the full suite, then use `superpowers:finishing-a-development-branch` for the merge/PR decision.
