# Installable Pricing Pipeline and Standalone Model Repositories

**Status:** Draft for user review; architectural direction approved

**Date:** 2026-08-26

**Target release:** `0.2.0`

## Summary

Convert this repository from a checkout-coupled application into an installable
Python framework. Real pricing models will live in separate confidential Git
repositories. Each model repository will pin the framework from the company
mirror, own its notebooks, SQL query, grouping decisions, configuration, and
`uv.lock`, and use one installed `pricing-pipeline` command for scaffolding,
schema operations, inspection, and reporting.

The chosen architecture is one framework distribution rather than several
small packages. It keeps the current `pricing_pipeline` Python namespace and
the current distribution name for compatibility. A future private package
index may distribute wheels, but the initial work deployment uses a company
Git repository pinned by full commit SHA.

## Goals

1. Install `pricing_pipeline` without cloning its source beside a model.
2. Give each deployable model family an independent repository and lockfile.
3. Expose supported commands through `uv run pricing-pipeline ...`.
4. Package SQL Server migrations, SQLite DDL, and scaffold templates inside the
   distribution.
5. Generate a standalone, notebook-first model project with this order:

   ```text
   01_data_ingestion.ipynb
   02_model_exploration.ipynb
   03_model_training.ipynb
   04_model_editor.ipynb
   05_manual_adjustment.ipynb
   06_model_deployment.ipynb
   ```

6. Put the model's tracked source query in `sql/model_data.sql` and load it with
   `pathlib` from notebook 01.
7. Allow notebook 02 to start from no groupings or existing approved groupings,
   inspect and edit them, and hand them to notebook 03 without first publishing
   a RAW model.
8. Preserve the existing governed SQL lifecycle, SQLite parity, semantic model
   deduplication, deployment views, manual edits, and monitoring variants.
9. Keep the personal-to-work framework sync strictly one way.

## Non-goals

- Store fitted models, datasets, credentials, notebook outputs, or confidential
  extracts in either framework Git repository.
- Create a Git repository for every weekly fit. A repository represents a
  deployable model family; runs and variants remain SQL records and external
  artifacts.
- Make SQL execute Python grouping logic. SQL remains the governed registry and
  relativity store.
- Automate `git init`, create company remotes, or infer a company's private Git
  URL.
- Split the framework into core, CLI, schema, and reporting distributions.
- Expand Python-version support during this refactor. Compatibility changes can
  be considered separately.
- Replace the SharePoint/network artifact store design.

## Alternatives considered

### A. One installed framework and separate model repositories — chosen

One versioned distribution owns reusable code, migrations, templates, and the
CLI. Model repositories contain only model-specific source and pin one reviewed
company commit. This provides reproducible upgrades, clean access boundaries,
small model pull requests, and a single schema authority.

### B. Git template or submodule per model — rejected

This is initially simple but duplicates implementation into every model,
creates ambiguous upgrade state, encourages local patches, and makes it hard to
prove which framework code produced a publication.

### C. Several framework distributions — deferred

Separate core, SQL, reporting, and CLI packages could reduce dependency size,
but they introduce cross-package compatibility and release coordination before
there is evidence that the single internal package is too large.

## Current blockers

The refactor must solve these concrete issues, not just add an executable name:

- `pyproject.toml` has no build backend, explicit package selection, or console
  entry point. The current lock records the project as virtual rather than an
  installed distribution.
- Generated notebooks search for sibling `pricing_pipeline/` and
  `pricing_models/` directories and mutate `sys.path`.
- SQLite DDL and SQL Server migrations live outside `pricing_pipeline` and are
  located through repository-relative paths.
- Commands live in `scripts/`, import the `scripts` namespace, and derive paths
  from repository layout.
- Renumbering notebooks without changing source hashing would hash exploration,
  omit governed training, and include deployment because the current logic
  relies on numeric filename prefixes.
- Grouping export currently requires an editor session opened from an already
  published RAW `Candidate`, which conflicts with exploration preceding
  training.
- Framework version is not recorded alongside Python and SuperGLM versions in
  durable model-run evidence.

## Framework package

### Build and layout

Use a PEP 517 build with Hatchling and an explicit `src` layout:

```text
src/pricing_pipeline/
├── __init__.py
├── __main__.py
├── cli/
├── data/
├── infra/
├── modeling/
├── models/
├── orchestration/
├── publishing/
├── reporting/
├── resources/
│   ├── migrations/
│   ├── offline_sqlite/
│   └── scaffold/
└── workbench/
```

The build configuration explicitly packages only `src/pricing_pipeline`.
Real model projects, `state/`, tests, documentation, private runtime modules,
and developer scripts must not enter the wheel.

Use the project version in `pyproject.toml` as the single authority.
`pricing_pipeline.__version__` resolves it with `importlib.metadata.version`.
Keep the current distribution name during this change so existing Git pins do
not need another migration. Keep `pricing_pipeline` as the import namespace.

Bound SuperGLM to the tested minor line, initially `>=0.26,<0.27`, because the
grouping bridge and some metadata extraction deliberately touch private fitted
state. A newer SuperGLM minor is adopted by an explicit framework release after
compatibility tests pass.

The published dependency contract is:

- **base:** `joblib`, `numpy`, `openpyxl`, `pandas`, `pyarrow`, `packaging`,
  `pydantic`, `python-dotenv`, `scikit-learn`, `sqlalchemy`, and the bounded
  `superglm` version;
- **`sqlserver`:** `pyodbc`;
- **`azure`:** `azure-identity` and `pyodbc`;
- **`report`:** `plotly` and `scipy`;
- **`scratch`:** `matplotlib`, `scipy`, CatBoost, LightGBM, and XGBoost; and
- **`mlflow`:** `mlflow`.

Model repositories normally install `[sqlserver,report]` and opt into
`scratch` only where exploration needs boosted benchmarks. Developer tools
(`pytest`, Ruff, SQLFluff, PyYAML, and build inspection) remain development
dependencies. `requirements.txt` stops being an independently maintained
authority; a legacy file, if still required, is generated from the lock.

### Packaged resources

Move the authoritative migration chain and offline DDL underneath
`pricing_pipeline.resources`. Access them with `importlib.resources.files()`;
use `as_file()` for APIs that require a filesystem directory. Explicit path
overrides such as `PRICING_SCHEMA_DIR` remain available for development and
diagnostics, but installed defaults never walk outside the package.

There must be one canonical copy of every executable SQL resource. Documentation
may link to its package location but must not maintain a second runnable copy.

Scaffold notebook templates and placeholder SQL are also installed resources.
Templates must not depend on the framework checkout.

### Public CLI

Add one console entry point:

```toml
[project.scripts]
pricing-pipeline = "pricing_pipeline.cli:main"
```

The supported interface is:

```text
pricing-pipeline scaffold ...
pricing-pipeline scaffold --upgrade --dry-run ...
pricing-pipeline schema status ...
pricing-pipeline schema apply ...
pricing-pipeline schema reset ...
pricing-pipeline schema reset-experiments ...
pricing-pipeline package inspect ...
pricing-pipeline report build ...
```

`python -m pricing_pipeline ...` invokes the same parser as a fallback. CLI
implementations accept an argument list, return integer exit codes, and lazily
import optional dependencies after subcommand selection. Stable notebook-facing
Python functions remain under `pricing_pipeline.notebook`; the CLI is not the
programmatic API.

For one compatibility release, existing public `scripts/*.py` commands become
thin wrappers around packaged CLI functions. Demos, portable-source generation,
local service launchers, and documentation rendering remain repository-developer
tools and are not public commands.

The compatibility map is exact:

| Existing command | Installed command |
|---|---|
| `scaffold_pricing_model.py` | `pricing-pipeline scaffold` |
| `apply_schema.py` | `pricing-pipeline schema apply` |
| `reset_remote_pricing_schema.py` | `pricing-pipeline schema reset` |
| `reset_pricing_experiments.py` | `pricing-pipeline schema reset-experiments` |
| `inspect_rating_package.py` | `pricing-pipeline package inspect` |
| `build_underwriter_report.py` | `pricing-pipeline report build` |

These wrappers warn in `0.2.x` and are removed no earlier than `0.3.0`.
`pricing_db.py` and `render_schema_sql.py` become internal package modules.
All other existing scripts remain repository-only tools unless a later design
promotes them deliberately.

Production containers install the built wheel with selected extras and do not
mount `pricing_pipeline`, `db`, or `scripts` through `PYTHONPATH`. An explicitly
named development Compose profile may retain an editable source mount, but CI
must always include a clean-wheel container smoke so that editable mode cannot
hide missing package resources.

## Standalone model repository

### Generated tree

The user first runs `uv init --bare` in an empty directory, adds the company framework
dependency, and invokes the installed scaffold. `pyproject.toml` and `uv.lock`
are validated, unmanaged prerequisites: the scaffold neither creates nor
rewrites them. It populates the current directory or an explicit `--root`; it
does not create or configure Git remotes.

```text
claim_frequency/
├── pyproject.toml              # pre-existing; unmanaged by scaffold
├── uv.lock                     # pre-existing; unmanaged by scaffold
├── pricing_model.toml
├── model_spec.py                # shared canonical feature/model factory
├── groupings.toml
├── README.md
├── .gitignore
├── .env.example
├── 01_data_ingestion.ipynb
├── 02_model_exploration.ipynb
├── 03_model_training.ipynb
├── 04_model_editor.ipynb
├── 05_manual_adjustment.ipynb
├── 06_model_deployment.ipynb
├── sql/
│   └── model_data.sql
└── .local/                    # created at runtime and ignored
```

`groupings.toml` may be absent or contain no collapses. The scaffold may create
an empty documented file so an analyst can paste existing approved mappings.

Do not generate `pricing_models/`, a `pricing_pipeline/` source copy, or
`__init__.py`. The model repository is a consumer application, not a nested
package in the framework checkout.

`uv init --bare` is required because it creates only the unmanaged
`pyproject.toml`; `uv add --no-sync` creates the lock. The scaffold owns the
README and `.gitignore` in a new project. If either already exists with
different content, initial scaffold stops and prints an adoption diff rather
than merging or overwriting it.

### Root discovery and configuration

`pricing_model.toml` is the unique root marker and non-secret configuration.
Unknown sections and keys fail closed. It contains:

```toml
schema_version = 2
template_version = "standalone-v1"

[model]
name = "CLAIM_FREQUENCY"
label = "Claim frequency"
target = "claim_count"
model_type = "frequency"
deployment_slot = "CLAIM_FREQUENCY_UAT"
features = ["driver_age", "vehicle_band", "region"]
dataset_name = "claim_frequency_model_frame"
source_system = "pricing_warehouse"
primary_keys = ["policy_period_id"]
fit_mode = "fit_reml"
scoring = ["deviance", "nll", "gini"]

[source]
sql = "sql/model_data.sql"
data_as_of_column = "data_as_of"
support_files = []

[roles]
# Omit optional roles that are not used by this model.
sample_weight_column = "exposure"
export_weight_column = "exposure"
# offset_column = "log_exposure"
# offset_source_column = "exposure"
# offset_label = "log(exposure)"

[validation]
kind = "kfold"
n_splits = 5
shuffle = true
random_state = 42

[notebook_defaults]
database_mode = "local"
runtime_module = ""
expected_remote_database = ""

[manual_edit_defaults]
source_selector = "deployed"
carry_forward = true
```

It never stores credentials or permits `ALLOW_REMOTE_WRITES`. Every generated
notebook starts with remote writes disabled and requires an explicit review-time
edit.

Governed `[model]`, `[source]`, `[roles]`, and `[validation]` values come only
from tracked `pricing_model.toml` and cannot be overridden at execution time.
Operational configuration precedence is explicit CLI option, then process
environment, then `[notebook_defaults]`/`[manual_edit_defaults]`, then library
default. Every effective governed value is included in model-source identity.

The library does not implicitly load a `.env` file. Commands that need one
accept `--env-file` explicitly; the
resolved file must remain inside the model root unless a separately named
administrator option authorizes an external secret provider. Runtime modules
may use their normal company secret provider. Relative config, artifact, SQL,
and report paths resolve against the model root, never cwd or the installed
package. Existing host-specific `/opt/pricing/...` defaults are removed.

`scaffold`, `--help`, schema commands with explicit runtime arguments, and
repository-maintainer diagnostics may run without an existing model marker.
Notebook/model commands require exactly one valid marker.

`model_spec.py` is the single canonical Python definition used by notebooks 02
and 03. The scaffold gives it a small public contract:

```python
def build_raw_features() -> dict[str, object]: ...
def build_model(*, features: dict[str, object] | None = None) -> SuperGLM: ...
```

With no argument, `build_model()` must use a fresh mapping from
`build_raw_features()`. With an argument, it must preserve the same family,
link, fit controls, penalties, and non-feature settings while using that exact
mapping. The returned feature keys and order must equal tracked
`[model].features`. Notebook 02 may fit arbitrary scratch models, but the
grouping editor/export path always starts from this canonical factory.
Notebook 03 uses the same factory for RAW and applies approved groupings to a
fresh returned mapping for ROUTINE_EDIT. The governed model-definition digest
combines the canonical governed TOML, `model_spec.py` bytes, configured support
files, and normalized declared SuperGLM feature metadata. Exploration export
records that digest, and notebook 03 requires an exact match before consuming
its groupings.

The installed library loads this trusted model source with
`load_model_spec(MODEL_PROJECT)`. It resolves `model_spec.py` through the same
root-contained, no-symlink-escape resolver as SQL, uses a deterministic private
module name derived from model-root and source SHA rather than `sys.path`, and
validates both factory signatures and feature keys before returning the module.
This makes notebook behavior independent of cwd while keeping arbitrary model
code explicitly confined to the tracked model repository.

The installed library exposes `find_model_root(start=Path.cwd())`, which searches
the starting directory and its parents for exactly one valid marker. An explicit
root argument is available for automation. Missing, malformed, or ambiguous
roots raise a concise error. Notebooks never mutate `sys.path`.

### Source SQL

`sql/model_data.sql` is tracked model source. The placeholder demonstrates a
bound data-as-at parameter and deterministic ordering but contains no company
table names or values. Notebook 01 reads exactly the configured file:

```python
from pathlib import Path

from sqlalchemy import text

from pricing_pipeline.project import find_model_root, load_model_project

MODEL_ROOT = find_model_root(Path.cwd())
MODEL_PROJECT = load_model_project(MODEL_ROOT / "pricing_model.toml")
SQL_PATH = MODEL_PROJECT.resolve_tracked_file(MODEL_PROJECT.source.sql)
SOURCE_SQL = SQL_PATH.read_text(encoding="utf-8").strip()
if not SOURCE_SQL:
    raise ValueError(f"Model-data SQL is empty: {SQL_PATH}")

raw = pd.read_sql_query(
    text(SOURCE_SQL),
    pricing.engine,
    params={"data_as_of": DATA_AS_OF},
)
```

`resolve_tracked_file` rejects absolute paths, traversal, non-files, and any
resolved symlink target outside the model root, and revalidates immediately
before opening to narrow replacement races. SQL uses bind parameters rather
than string interpolation. The verified model frame, not a raw extract, is
stored under `.local/`.

## Notebook workflow

### 01 — Data ingestion

The only governed step that runs the model query and constructs the verified
model-frame artifact. It validates data-as-at, primary keys, roles, ordering,
and frame evidence. It does not fit or publish a model.

### 02 — Model exploration

Optional but strongly encouraged, repeatable, and SQL read-only. It loads the
verified frame, provides a blank modelling area, supports unconstrained GAM and
boosted benchmarks, starts from either existing `groupings.toml` or no
groupings, opens the SuperGLM editor, and exports reviewed grouping decisions.
It never publishes or deploys a model.

### 03 — Model training

The first governed model-publication step. It fits the untouched RAW model and,
when approved groupings exist, the ROUTINE_EDIT model on the same manifest and
validation evidence. Missing or empty grouping configuration skips
ROUTINE_EDIT explicitly.

### 04 — Model editor

Opens only a published candidate, produces an `EDITOR_EDIT` child, and preserves
manifest and parent lineage.

### 05 — Manual adjustment

Opens a deployed or explicitly selected published model, records a replayable
business policy, produces a `MANUAL_EDIT` child, and optionally performs an
explicit deployment. It never silently carries a policy forward.

### 06 — Deployment

Lists published candidates, shows enriched manifest/data-as-at/model-kind
evidence, compares with the current champion, and records deployment history.
It performs no fitting or editing.

## Grouping source and runtime artifact

The tracked `groupings.toml` is the durable, reviewable source of truth. The
Joblib file remains a generated runtime handoff, not the only record of a
business decision.

```text
groupings.toml                         tracked and diffable
        │
        │ validate/compile against verified frame
        ▼
.local/routine_groupings.joblib        actual LevelGrouping objects; ignored
.local/routine_groupings.joblib.json   integrity/provenance sidecar; ignored
```

The TOML schema records every feature's complete original level universe,
base/special-level declarations needed by grouping construction, and named
groups. Values retain unambiguous primitive type identity. For example:

```toml
format_version = 1

[features.coverage]
base = "CSP"
ordered = false
new_level_policy = "error"
original_levels = ["CSP_STANDARD", "CSP_PLUS", "OEM_STANDARD", "OEM_PLUS"]
special_levels = []

[features.coverage.groups]
CSP = ["CSP_STANDARD", "CSP_PLUS"]
OEM = ["OEM_STANDARD", "OEM_PLUS"]

[features.deductible]
base = "500_750"
ordered = true
new_level_policy = "error"
original_levels = [250, 500, 750, 1000]
special_levels = []

[features.deductible.groups]
"500_750" = [500, 750]
```

Group names are strings, while member values retain their TOML scalar types.
Final grouped-level labels are strings: a singleton uses the canonical string
form of its original value and a collapsed group uses its group name. `base`
and `special_levels` refer to those final labels. Typed identities whose
canonical labels collide are rejected rather than silently merged. For an
ordered categorical, `original_levels` is its semantic order,
members of one collapsed group must be contiguous, and final grouped order is
the order of first member appearance. For an unordered categorical,
`original_levels` is emitted in canonical typed-identity order.

Version 1 supports only `new_level_policy = "error"`; the field is explicit so
a future reviewed policy is a schema change rather than an implicit fallback.
An observed typed identity outside `original_levels` always blocks compilation.
Spline basis, knots, smoothing policy, and monotonic constraints are not level
groupings; they remain in governed model specification code consumed by
notebook 03. Categorical base and special-level declarations are included here
because they must be validated against the grouped level universe.

The accepted level scalar types are exact `str`, exact `int` (excluding
`bool`), exact `bool`, finite `float`, TOML local date, and TOML offset/local
datetime. Null/missing is not a grouping level: ingestion must map missing
business categories to an explicit named level before grouping. Unsupported
objects and non-finite floats fail closed. Canonical semantic identity uses a
type-tagged JSON representation, so values that render similarly cannot
collide. Feature and group keys are written in Unicode code-point order.
`original_levels` preserves configured order for ordered categoricals and uses
canonical typed-identity order for unordered categoricals; group members are
written in their `original_levels` order. Formatting, comments, or TOML table
order do not affect the semantic digest.

Validation rejects:

- overlapping group membership;
- duplicate or empty groups;
- ambiguous typed identities such as integer `1` versus string `"1"`;
- a configured member absent from the declared universe;
- a new observed level unless an explicit reviewed policy handles it; and
- invalid or unsupported scalar types.

Historical declared levels absent from a refresh remain in the bound level
universe rather than being silently deleted. New levels fail by default. This
makes frozen categorical structure explicit across refreshes.

Notebook 02 can load an existing config, fit an exploratory model with it,
allow editor changes, and atomically export a new deterministic config after
explicit replacement confirmation. It can also start with no groups and create
the initial config. Generated Joblib metadata binds the compiled objects to the
model name, verified frame SHA, data-as-at, grouping semantic SHA, Python,
SuperGLM, and framework versions.

The current requirement for a published RAW `Candidate` is removed from this
exploration export path. Notebook 02 does not register or persist a model.
Instead, a new immutable `ExplorationContext` is constructed from the parsed
`PricingModelSpec`, exact verified frame artifact/evidence, declared feature
specification, fitted exploratory model, and editor session. Export requires
the session's reference model to be the exact fitted model in that context and
records the frame, feature-specification, and grouping semantic digests. This
prevents an unrelated editor session being exported under false provenance.
Publication APIs retain their stronger Candidate requirements.

Notebook 03 recompiles or verifies the runtime artifact from tracked TOML
before fitting; it never trusts an arbitrary pickle. Joblib loading remains
restricted to locally trusted artifacts after size, hash, runtime, provenance,
and semantic checks.

An upgrade that finds an existing approved
`.local/routine_groupings.joblib(.json)` must not create an empty TOML. It runs
a dedicated converter that first performs all existing byte, sidecar, runtime,
model, frame, data-as-at, partition, and semantic checks, renders canonical
TOML into a review file, and requires explicit analyst confirmation before that
file becomes `groupings.toml`. If the legacy artifact cannot be verified under
its recorded runtime, the upgrade blocks and requires re-review in notebook 02.

Monitoring does not depend on `groupings.toml` at run time. Its frozen variants
inherit the exact grouping and level universe embedded in the deployed candidate.

## Governed source identity

Replace numeric filename-prefix filtering with semantic roles. The governed
model-source digest starts with the canonical `[model]`, `[source]`, `[roles]`,
and `[validation]` sections of `pricing_model.toml`. It excludes
`[notebook_defaults]` and `[manual_edit_defaults]`, which affect execution and
operator selection rather than fitted semantics. It then includes canonical
content from:

- `sql/**/*.sql`;
- `model_spec.py`;
- `01_data_ingestion.ipynb` source cells;
- `03_model_training.ipynb` source cells; and
- every relative regular file listed in `[source].support_files`.

Configured support files use the same root-contained, no-symlink-escape
resolver as SQL. Duplicate paths, directories, globs, and files outside the
model root are rejected.

The final digest is model-kind aware. RAW excludes grouping decisions.
ROUTINE_EDIT includes the canonical semantic digest of `groupings.toml`.
EDITOR_EDIT and MANUAL_EDIT inherit the parent model-source digest and add
their existing immutable submission or policy evidence. An absent grouping
file and a present semantic-empty grouping file share the same empty grouping
digest; because no ROUTINE_EDIT is created in either case, that equivalence
cannot erase a real grouped run.

It excludes notebook outputs and the exploratory/editor/manual/deployment
notebooks (`02`, `04`, `05`, and `06`). Those steps create their own immutable
submission, policy, artifact, receipt, or deployment evidence. Tests assert
inclusion by role, never by numeric prefix.

## Scaffold safety and upgrades

### Initial scaffold

`pricing-pipeline scaffold` first verifies the pre-existing `pyproject.toml`
and `uv.lock`, then preflights the complete managed output tree before writing.
It rejects managed ancestor and leaf symlinks, absolute or escaping paths, and
conflicting existing files. Each new file is written to a same-filesystem
temporary and atomically installed. An identical retry is a true no-op,
including mtimes.

Blanket `--force` replacement is retired. Scaffold and upgrade never overwrite
a customized notebook. The operator resolves custom content manually and then
reruns validation.

### Upgrade

`pricing-pipeline scaffold --upgrade --dry-run` inventories the project and
prints the proposed migration without mutation. A real upgrade:

- requires a valid root marker or an explicitly recognized legacy layout;
- knows historical template checksums and stable managed-cell identifiers;
- transforms only a complete known template or unmodified managed cells;
- treats an ambiguous customized notebook as an incomplete manual migration,
  leaves it byte-for-byte unchanged, and does not advance `template_version`;
- stages all replacement bytes and a journal before applying per-file atomic
  moves;
- aborts with zero changes on collisions, partial layouts, symlinks, or unknown
  notebook roles; and
- never runs Git commands or moves a project into another repository.

A legacy layout with no marker requires an explicit reviewed
`--project-config <path>` containing every governed field. The upgrader may
extract suggestions from cells whose complete historical template fingerprint
is known, but it never treats suggestions as approved input. It stages the
reviewed config as `pricing_model.toml`, validates that `model_spec.py`, SQL,
roles, validation, and notebook managed cells agree with it, and keeps the
upgrade incomplete until all required fields and digests validate.

Multi-file replacement cannot be crash-atomic. The guarantee is therefore:
complete preflight before mutation, per-file atomic replacement, journaled
backups, rollback for any caught in-process failure, and explicit crash
recovery. The journal and backups are fsynced before the first move. On a later
invocation, an unfinished journal blocks normal operation and offers verified
`--recover-old` or `--recover-new` completion. Tests inject failure before and
after every journalled move. The scaffold never claims success or advances the
marker version while recovery is pending.

Legacy notebook mappings are:

```text
99_scratch_work.ipynb       -> 02_model_exploration.ipynb
02_model_training.ipynb     -> 03_model_training.ipynb
03_model_editor.ipynb       -> 04_model_editor.ipynb
04_manual_adjustment.ipynb  -> 05_manual_adjustment.ipynb
05_model_deployment.ipynb   -> 06_model_deployment.ipynb
04_model_deployment.ipynb   -> 06_model_deployment.ipynb  # oldest layout
```

If old and new targets coexist, the upgrade stops for manual reconciliation.
It never scrapes arbitrary analyst SQL out of a customized ingestion notebook.
Known untouched historical templates may be migrated automatically; otherwise
the dry run explains how to create `sql/model_data.sql`, replace checkout-based
imports/root discovery, and complete managed cells manually. A subsequent dry
run must verify the standalone contracts before the upgrade may finish.

Moving `pricing_models/<name>/` into its own Git repository is a separately
documented operator action so Git history and company permissions remain under
human control. The default extraction creates a new empty repository and copies
only an allowlisted snapshot of reviewed model source. It must not clone the
framework history and then delete other paths, because deleted data remains in
reachable Git objects. Preserving selected history is an advanced path that
requires verified path filtering followed by a scan of every reachable ref and
object before the first company push.

## Confidentiality defaults

Every standalone model scaffold generates at least:

```gitignore
.local/
state/
data/
artifacts/
secrets/
.env
.env.*
!.env.example
*.sqlite*
*.joblib
*.pkl
*.pickle
*.parquet
*.feather
*.arrow
*.csv
*.xlsx
.ipynb_checkpoints/
__pycache__/
.venv/
```

Notebooks, `pricing_model.toml`, `groupings.toml`, `pyproject.toml`, `uv.lock`,
and `sql/model_data.sql` remain tracked. CI rejects notebook outputs and scans
tracked paths for prohibited data/artifact patterns. `.gitignore` is only a
guardrail; confidential content must never enter framework Git history.

The framework repository contains synthetic examples only. Work model
repositories and their company SQL must never be added to the personal
framework remote.

Before the first company-framework push and for every imported upstream range,
automated checks scan all reachable refs/history—not only the working tree—for
credentials, prohibited data/artifact extensions, notebook outputs, and known
confidential paths. A clean `.gitignore` result cannot substitute for this
history scan.

## Personal-to-work release flow

### Remote topology

On the work clone:

```text
origin  company framework repository; fetch and push
home    personal upstream; fetch only
```

The work machine must use anonymous access or a read-only credential for the
personal repository and must not store a writable personal credential. In
addition, configure an invalid `home` push URL, restrict its fetch refspec to
the intended branch, disable automatic tag fetching, set `origin` as the
default push remote, and set `push.default=nothing`:

```bash
git remote set-url --push home disabled://work-to-personal-push-prohibited
git config --local remote.home.tagOpt --no-tags
git config --local --replace-all remote.home.fetch \
  +refs/heads/main:refs/remotes/home/main
git config --local remote.pushDefault origin
git config --local push.default nothing
```

Setup verifies `git remote -v`, `git remote get-url --push home`, the fetch
refspec, tag policy, and credential capability. Configuration is defence in
depth; the read-only credential is the enforceable boundary. Never push
directly to a personal URL and never use `git push --mirror`, `--all`, or
unreviewed `--tags` from work.

### Import

1. Create a signed personal release tag from a clean, verified `main` using an
   approved key. If signing is unavailable, verify the full source SHA through
   an independent trusted channel. Personal release refs must be protected from
   force update.
2. At work, fetch that exact tag without broadly importing tags.
3. Verify the tag/full SHA and audit changes, especially workflow files,
   dependency URLs, build configuration, binaries, notebook outputs, and locks.
4. Merge the tag with preserved ancestry into `import/framework-vX.Y.Z`.
5. Run locked clean-install, build, full tests, lint, format, resource, and
   confidentiality checks.
6. Open and merge a company-side PR containing the personal tag/SHA and previous
   imported SHA.
7. Protect a company release ref/tag pointing to the reviewed company merge
   commit so old model pins remain fetchable. Model repositories depend only on
   that full company commit.

Do not squash the personal import commit because preserved ancestry makes the
next upstream delta auditable. Company feature work does not travel back to the
personal repository through this mechanism. Every consumable framework tree
has a unique PEP 440 version: a tree-identical personal import may retain its
upstream version, while any company-only code change requires a new company
version and protected company tag before a model may pin it.

### Model dependency

A model repository pins the complete company commit and commits its own lock:

```bash
uv add --no-sync \
  "airflow-superglm-builder[sqlserver,report] @ git+ssh://git@company.example/pricing/airflow_superglm_builder.git@<40-hex-company-commit>"
git diff -- pyproject.toml uv.lock
uv lock --check
uv sync --locked
```

The framework lock governs framework CI only; it does not govern consumers.
Each model's `uv.lock` is its execution authority. Upgrade by changing the
company commit with `uv add --no-sync` in a dedicated dependency-only commit and
PR, inspecting the complete lock diff before environment sync. Rollback by
reverting that dedicated dependency-upgrade commit and running `uv sync --locked`.

A future company CI release may build and immutably publish wheels to a private
index. It must retain the same import, CLI, resource, and provenance contracts.

## Database compatibility and provenance

SQL Server migrations remain append-only and authoritative. Packaged schema
commands keep the existing database-name guard, execution lock, migration
checksums, dry-run reset, and explicit destructive confirmation.

Define one immutable `FrameworkBuildIdentity` containing distribution name,
PEP 440 version, build kind (`GIT`, `WHEEL`, or `EDITABLE`), and full 40-hex
source commit SHA. A Git install obtains and verifies the company commit from
PEP 610 direct-reference metadata. Company wheel CI embeds a generated build
identity resource containing the protected company source commit and release
tag; the model lock retains the wheel archive hash. An arbitrary editable or
dirty source tree is marked `EDITABLE` and may explore locally but cannot make
governed remote writes.

Persist the complete build identity in candidate artifact envelopes,
publication receipts and lineage, monitoring contracts, SQL Server model-run
evidence, and SQLite alongside Python and SuperGLM versions. New successful
governed runs require a valid version and non-null 40-hex company source SHA for
both Git and wheel builds. The first implementation migration adds nullable
columns, labels legacy rows `LEGACY_UNKNOWN`, and uses triggers/application
validation to require the identity for new successful runs. SQLite receives
equivalent columns and upgrade logic.

Every framework release ships the ordered filename and SHA-256 of every known
migration plus its supported schema API-version range. The database records a
schema API version separately from the latest migration. Additive,
backward-compatible migrations retain the API version; a migration that breaks
older writers must increment it. Schema status validates the complete applied
set, not merely the greatest filename:

- **UNINITIALIZED:** tracking table absent. Status and guarded apply/reset are
  available; governed writes are blocked.
- **BEHIND:** applied rows are an exact checksum-valid prefix of the packaged
  chain. Status and apply are available. Governed writes are allowed only when
  the database API version is in the framework's supported range and the
  database has reached the framework's declared minimum required migration.
- **CURRENT:** the complete packaged chain matches and the API version is
  supported. Governed writes are allowed.
- **AHEAD:** every packaged migration matches and additional strictly later
  migrations exist. Reads/status remain available, but governed writes always
  block because this older distribution cannot authenticate unknown migration
  contents. Upgrade the framework to one that packages and checksums them.
- **DIVERGED:** missing/interleaved filenames or non-prefix history. Status and
  destructive reset dry-run remain available; apply and governed writes block.
- **CHECKSUM_MISMATCH** or **FAILED:** any known checksum differs or the tracker
  records a failed/incomplete application. Only status and explicitly confirmed
  disposable reset remain available.

Apply is transactional and inserts its tracking row only after success. The API
version is changed in the same migration transaction. This explicit
compatibility contract lets model repositories upgrade deliberately rather
than simultaneously while still blocking an old writer after a breaking schema
change.

Notebook connection preflight reports:

- installed framework version and full direct-reference commit when available;
- database's complete migration-set status and checksum evidence;
- whether that database schema is compatible with the installed framework; and
- an actionable schema command when it is behind.

It must not silently apply migrations from a notebook.

## Error handling

- All read or validation failures occur before external writes.
- CLI errors identify the model/config/path field but never include credentials,
  raw rows, category values prohibited by privacy policy, or artifact bytes.
- Scaffold creation is all-preflighted and per-file atomic. Upgrade failures
  caught in-process roll back from the journal; process/filesystem interruption
  leaves a detectable recovery journal and never reports success.
- Missing optional dependencies produce a command-specific installation hint;
  unrelated CLI commands remain usable.
- Unsupported grouping/runtime versions require explicit recompilation or
  framework upgrade; they are never silently coerced.
- Schema mismatch blocks SQL writes while leaving local exploration available.

## Verification strategy

### Packaging and clean-room installation

- Build wheel and sdist and inspect them for all migrations, offline DDL,
  templates, metadata, and only intended Python packages.
- Install the wheel in a new environment, change cwd outside the checkout, and
  verify imports, CLI help, packaged migration discovery, and SQLite bootstrap.
- Remove `pytest`'s repository `pythonpath` escape hatch; tests exercise the
  installed package.
- Verify the legacy wrapper commands delegate to the same parser.

### Standalone scaffold

- Scaffold into an empty external directory and assert the exact golden tree,
  strict config, notebook names/order, empty outputs, and no `sys.path` mutation.
- Execute/compile notebook setup cells using only site-packages.
- Verify marker discovery from root and descendants and reject invalid,
  escaping, symlinked, or ambiguous roots.
- Assert notebook 01 reads exactly `sql/model_data.sql` through `pathlib` and
  SQLAlchemy bind parameters.
- Validate idempotent retry, dry-run, atomic failure, customized-file
  preservation, every legacy mapping, and no-change-on-conflict.

### Groupings and governed identity

- Cover empty, existing, editor-created, multiple-feature, multiple-group,
  typed-level, overlap, new-level, missing-historical-level, and version-upgrade
  cases.
- Prove the generated Joblib object matches canonical TOML semantics and is
  rejected after byte, frame, provenance, or runtime tampering.
- Prove notebook 02 performs no SQL write and notebook 03 is the first model
  publication step.
- Prove source hashes change for governed config/SQL/01/03/supporting code and
  do not change for 02/04/05/06 or notebook outputs.
- Prove every sample/export-weight and offset-role change alters both RAW and
  ROUTINE_EDIT source identity.
- Prove changing only `groupings.toml` leaves RAW identity unchanged, changes
  ROUTINE_EDIT identity, and invalidates an exploration grouping handoff whose
  recorded model-definition/grouping digest no longer matches.

### Release and confidentiality

- Test version/tag/source-SHA equality and propagate the complete mandatory
  framework build identity through artifact, publication, monitoring, SQL
  Server, and SQLite evidence.
- Use `git check-ignore` assertions for every generated sensitive artifact type
  while proving SQL/config/notebooks remain trackable.
- Run existing full SQL migration, SQLite, publication, deployment, manual-edit,
  monitoring, reporting, notebook, and confidentiality suites.

## Delivery sequence

1. **Package foundation:** build backend, `src` layout, version source,
   packaged SQL/templates, clean-room wheel tests.
2. **CLI:** common parser, scaffold/schema/inspect/report commands, module entry,
   compatibility wrappers.
3. **Standalone project:** root marker/config, model tree, SQL loading, new
   notebook order, role-based source hashing, confidentiality defaults.
4. **Grouping bridge:** tracked TOML, exploration compiler/editor export,
   generated Joblib, notebook 03 consumption.
5. **Safe upgrade:** dry-run, template fingerprints, journaled legacy notebook
   migration/recovery, operator guide for extracting model repositories.
6. **Governance:** framework-version artifact and SQL evidence, compatibility
   preflight, SQLite parity.
7. **Release:** company import runbook, immutable tag/commit validation, example
   standalone model repository smoke test.

Each delivery step ends with its focused tests and a clean-room installed-wheel
smoke. The final release requires the entire existing suite plus the new
standalone-consumer suite.

## Acceptance criteria

The design is complete when all of the following are true:

1. From an empty directory outside this checkout, a user can install the
   company-pinned framework and run `uv run pricing-pipeline scaffold ...`.
2. The generated model repository has exactly the six numbered notebooks,
   `pricing_model.toml`, `model_spec.py`, optional `groupings.toml`, and
   `sql/model_data.sql`.
3. Generated notebooks import only the installed library and work from any cwd
   inside the model repository.
4. Notebook 02 supports no grouping or existing grouping input and can export
   reviewed decisions without a published RAW package.
5. Notebook 03 publishes RAW and optional ROUTINE_EDIT models with full manifest,
   data-as-at, grouping, split, framework, Python, and SuperGLM evidence.
6. Schema and SQLite commands use installed package resources by default;
   explicit development overrides are isolated and separately tested.
7. Scaffold retry and upgrade never overwrite customized files or follow
   symlinks; writes are per-file atomic, caught failures roll back, and crashes
   leave a mandatory recoverable journal rather than a false success.
8. Model source hashing follows semantic roles rather than numeric filename
   prefixes.
9. A model repository is reproducible from its tracked source and `uv.lock`
   without the framework checkout.
10. No work model, query, data, artifact, credential, or work-only change can be
    pushed through the configured personal remote, and first-push/import checks
    cover every reachable Git ref rather than only the current tree.
