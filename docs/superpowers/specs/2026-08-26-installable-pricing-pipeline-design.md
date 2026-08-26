# Installable Pricing Pipeline and Standalone Model Repositories

**Status:** Revised after architecture review; awaiting final approval

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

The published dependency contract retains every compatibility bound already
proved by the current lock and adds bounds deliberately when code relies on a
specific public API. The initial contract is:

- **base:** `joblib`, `numpy`, `openpyxl`, `pandas`, `pyarrow>=23.0.1`,
  `packaging`, `pydantic>=2.13,<3`, `python-dotenv`, `scikit-learn`,
  `sqlalchemy`, and the bounded `superglm` version;
- **`sqlserver`:** `pyodbc`;
- **`azure`:** `azure-identity` and `pyodbc`;
- **`report`:** `plotly>=6.9` and `scipy`;
- **`notebook`:** `ipykernel` (with JupyterLab remaining an analyst-tool choice);
- **`scratch`:** `matplotlib`, `scipy`, CatBoost, LightGBM, and XGBoost; and
- **`mlflow`:** `mlflow`.

Model repositories normally install `[sqlserver,report,notebook]` and opt into
`scratch` only where exploration needs boosted benchmarks. Their lock provides
the exact transitive environment. Developer tools (`pytest`, Ruff, SQLFluff,
PyYAML, and build inspection) remain framework-development dependencies.
`requirements.txt` stops being an independently maintained authority; a legacy
file, if still required, is generated from the lock. Changing a lower or upper
compatibility bound requires a release note and clean-wheel compatibility test;
the packaging refactor must not silently widen or narrow supported APIs.

### Packaged resources

Move the authoritative migration chain and offline DDL underneath
`pricing_pipeline.resources`. Access them with `importlib.resources.files()`;
use `as_file()` for APIs that require a filesystem directory. Packaged resources
are the only authority for governed remote apply/reset and publication
preflight. `PRICING_SCHEMA_DIR` is removed from governed command resolution.
An explicit `--development-resource-dir` remains available only for diagnostics
and disposable local databases after a second noncanonical-resource
confirmation; it marks the resulting schema `NONCANONICAL` and permanently
blocks governed remote writes until reset from packaged resources. It is never
read implicitly from an environment variable.

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
scaffold_state = "current"

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

This example is illustrative; the following rules are the normative version-2
schema:

| Section | Required fields | Optional/default fields |
|---|---|---|
| root | exact positive integer `schema_version = 2`, exact supported `template_version`, `scaffold_state` | none |
| `[model]` | non-empty `name`, `label`, `target`, `deployment_slot`, `dataset_name`, `source_system`; `model_type` in `frequency`, `severity`, `burn_cost`; non-empty unique ordered `features` and `primary_keys`; `fit_mode` in `fit`, `fit_reml` | non-empty unique `scoring`, default `['deviance', 'nll', 'gini']`, limited in v2 to those three stable metric IDs |
| `[source]` | root-relative regular-file `sql`; non-empty `data_as_of_column` | unique ordered `support_files = []` |
| `[roles]` | none | optional non-empty `sample_weight_column`, `export_weight_column`, `offset_column`, `offset_source_column`, and `offset_label` |
| `[validation]` | one discriminating `kind` and the fields required by that kind | only the kind-specific defaults below |
| `[notebook_defaults]` | none | operational `database_mode`, `runtime_module`, `expected_remote_database` |
| `[manual_edit_defaults]` | none | operational `source_selector`, `carry_forward` |

Names are stripped non-empty strings, model/features/roles must refer to distinct
columns where their semantics require it, and role columns must be present in
the verified frame. `offset_source_column` and `offset_label` are permitted only
with an offset contract that exports a factor; `export_weight_column` is
permitted only when its publication contract uses it. Unknown or inapplicable
fields fail closed rather than being ignored.

`scaffold_state` is exactly `current` or `manual_pending`; notebook/model
commands require `current`. `template_version` must be one the installed
framework can validate, not merely a non-empty string.

`[validation]` is a discriminated union matching the existing notebook API:

- `kind = "kfold"`: required `n_splits >= 2`; defaults `shuffle = true`,
  `random_state = 42`, `materialize = false`. `random_state` must be absent
  when `shuffle = false`.
- `kind = "train_test_split"`: required finite `0 < test_size < 1`; defaults
  `shuffle = true`, `random_state = 42`, `materialize = false`; optional
  `stratify_column` is valid only when shuffling and must name a frame column;
  `random_state` is absent when shuffling is false.
- `kind = "column_kfold"`: required `column`; default `materialize = false`;
  random/test-size/shuffle fields are forbidden.
- `kind = "column_holdout"`: required `column` and non-empty, disjoint,
  typed-TOML `train_values` and `test_values`; default `materialize = false`;
  random/test-size/shuffle fields are forbidden.

Canonical validation identity includes the discriminant, all effective defaults,
typed values, and the exact split indices/row-order evidence produced by the
splitter. A versioned parser registry accepts only explicitly supported config
versions. Each older version has one deterministic adapter to the current
in-memory model or an actionable rejection; unknown newer versions always
block. Golden fixtures cover every version and validation kind. A schema-version
upgrade is written only after the adapted configuration has been printed and
explicitly approved.

The file never stores credentials or an `ALLOW_REMOTE_WRITES` switch. Remote
authorization is deliberately outside governed source. Interactive notebooks
obtain a short-lived, non-serializable `RemoteWriteCapability` by calling a
library prompt that requires the operator to enter the expected database and a
fixed destructive/write acknowledgement at execution time. Automation uses the
equivalent explicit CLI flags. The capability is bound to the current process,
connection identity, expected database, verified framework/project identities,
and schema preflight, and every lowest-level remote mutation API requires it.
Notebook source therefore remains unchanged between read-only and write runs;
the capability and acknowledgement never enter notebook cells, files, model
source identity, or artifacts.

Governed `[model]`, `[source]`, `[roles]`, and `[validation]` values come only
from tracked `pricing_model.toml` and cannot be overridden at execution time.
Operational configuration precedence is explicit CLI option, then process
environment, then `[notebook_defaults]`/`[manual_edit_defaults]`, then library
default. Every effective governed value is included in model-source identity;
root scaffold metadata and operational defaults are excluded.

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

### Model-project provenance

Define an immutable, versioned `ModelProjectBuildIdentity` for every governed
publication. It contains:

- a credential-free normalized company model-repository identifier;
- the full 40-hex `HEAD` commit;
- the exact SHA-256 of committed `pyproject.toml` and `uv.lock` bytes;
- the framework direct-reference commit parsed from both files;
- a canonical path/blob manifest SHA for every governed model-project file; and
- a clean-state assertion produced by comparing the index, tracked worktree,
  and non-ignored untracked paths with `HEAD`.

Ignored runtime paths such as `.local/` do not make a project dirty. Any tracked
change, staged change, unresolved merge, submodule, replace/graft state, or
non-ignored untracked file does. The identity validator requires
`pyproject.toml`, `uv.lock`, every governed source file, and the current commit
to exist in one ordinary repository; it rejects shallow/missing commit objects
when the configured company remote cannot resolve the commit. It also requires
the framework commit in the lock/direct reference to equal the installed
`FrameworkBuildIdentity`.

Dirty, uncommitted, non-Git, or locally forked projects may ingest, explore, and
fit into `.local/`, with an explicit `LOCAL_UNBOUND` identity. They cannot
publish, edit, manually adjust, monitor, or deploy remotely. Remote publication
requires a clean committed `ModelProjectBuildIdentity`; its complete fields are
persisted through the frame handoff, candidate envelope, publication receipt,
model run, monitoring evidence, SQL Server, SQLite, and deployment views. A
content digest is therefore both verifiable and locatable at a protected company
repository revision. Publication records cross-link this project identity and
the separate semantic model-source SHA; neither digest contains the other, so
their construction is acyclic.

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
fresh returned mapping for ROUTINE_EDIT.

The library constructs a canonical, versioned `UnfittedModelContract` from the
returned object rather than trusting source bytes alone. It records the exact
family/distribution and parameters (including Tweedie power where applicable),
link, intercept policy, exposure/offset semantics, fit and REML controls,
penalty/smoothing configuration, interaction structure, and the complete
ordered feature contract. Each feature record includes its concrete feature and
basis type, dtype semantics, base/special levels, level order, knots or knot
policy, `n_knots`, basis width/degree, extrapolation, monotonic constraints,
penalty controls, and every other public value that can change the design matrix
or fitted objective. It excludes learned coefficients, fitted lambdas, caches,
and editor/runtime state. Unsupported or privately opaque prediction-authority
state blocks governed publication until the SuperGLM compatibility bridge can
canonicalize it.

The governed `ModelDefinitionIdentity` combines the effective model-definition
fields from `[model]` and `[roles]`, `model_spec.py` bytes, configured
support-file bytes, and the canonical raw `UnfittedModelContract`.
Ingestion/source-system and validation fields remain in their dedicated
identities rather than being double-counted here. RAW binds the raw definition
identity directly. ROUTINE_EDIT binds the same raw identity plus the grouping
semantic SHA and canonical effective grouped-feature contract. Exploration
export records these identities, and notebook 03 reconstructs and requires exact
equality before consuming its groupings. Operational authorization and notebook
defaults never enter either contract.

The installed library loads this trusted model source with
`load_model_spec(MODEL_PROJECT)`. It resolves `model_spec.py` through the same
root-contained, no-symlink-escape resolver as SQL, uses a deterministic private
namespace package and module name derived from model-root and source SHA rather
than `sys.path`, and validates both factory signatures and feature keys before
returning the module. Relative imports such as `from .model_helpers import ...`
resolve inside that private namespace. After loading, every imported module
whose origin is under the model root must be a regular, root-contained file
declared in `[source].support_files`; undeclared local imports, namespace-path
escape, dynamic files without stable bytes, and symlinked helpers block. This
makes notebook behavior independent of cwd while keeping arbitrary model code
explicitly confined to the tracked model repository. Support files may be
Python or data, but all are byte-hashed and have one declared root-relative
path.

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

Notebook 01 constructs a versioned immutable `IngestionSourceIdentity` before it
executes SQL. Its canonical digest binds:

- the effective ingestion-relevant `[model]`, `[source]`, and `[roles]` fields
  from `pricing_model.toml`, including primary-key/order declarations;
- exact normalized bytes of the configured SQL file and each ingestion support
  file;
- normalized source cells of the installed-template role
  `data_ingestion` (not a numeric filename assumption);
- canonical typed bind parameters, including the exact data-as-at value;
- the query/runtime adapter identity and source-system identifier; and
- the declared column-role, primary-key, deterministic-order, and expected-frame
  contract.

Credentials, connection strings, host names, and remote-write authorization are
never included. The SQL bytes actually passed to SQLAlchemy and the bind values
actually passed to the driver must hash to this identity; changing a file after
preflight causes execution to abort rather than producing a receipt for
different bytes.

After query and frame validation, notebook 01 constructs
`IngestionBuildIdentity` from that source identity plus the observed frame
schema, model-frame SHA, row-order SHA, exact data-as-at, row/column counts, and
validation outcome. The source identity can therefore be computed before an
external read, while the build identity proves what that exact read produced.

`ModelFrameArtifact` advances to a versioned envelope that stores the complete
ingestion identity, its SHA-256, the model-frame SHA, exact data-as-at, row-order
SHA, and the `ModelProjectBuildIdentity` state observed at ingestion. Loading the
frame verifies artifact bytes and then recomputes the current ingestion source
identity. Notebooks 02 and 03 require an exact source match before deserializing
or using the frame. Editing SQL, governed config, notebook-01 source, support
files, query parameters, or role/order declarations therefore makes an older
frame stale and requires rerunning notebook 01. A later Git commit that contains
identical ingestion source does not invalidate the frame; remote publication
separately requires the current clean committed project identity.

The legacy v1 frame envelope remains readable for inspection and local
exploration, but because it contains no ingestion identity it is never eligible
for notebook-03 publication. The actionable upgrade is to rerun notebook 01;
the framework never guesses provenance for old frame bytes.

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
- a collapsed group name that equals any surviving singleton final label or
  another group's canonical final label;
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
model name, verified frame and ingestion SHA, model-definition SHA, data-as-at,
grouping semantic SHA, Python, SuperGLM, framework-build, and model-project
identities.

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
model, frame, data-as-at, partition, and semantic checks. Legacy v1 grouping
objects stringify original values and do not record ordered/base/special facts,
so they are not presumed to contain typed version-1 TOML semantics.

Automatic canonical conversion is permitted only when a freshly loaded verified
parent candidate, the canonical raw model feature contract, the legacy grouping
object, and the verified typed frame provide a unique one-to-one identity for
every original level—including historical levels absent from the current frame—
and agree on ordering, base, and special declarations. This is expected to be
rare. Otherwise the converter writes only
`.local/groupings-conversion-review.toml`, a deliberately non-consumable review
template containing the legacy string mapping plus explicit unresolved fields.
It must never be named or accepted as `groupings.toml`. Notebook 02 shows the
analyst each ambiguity and requires typed values, full historical universe,
order, base, special levels, and collision-free final labels to be supplied and
reviewed. Only a newly validated canonical export becomes `groupings.toml`.
Unverifiable runtime or provenance blocks even review-template extraction and
requires reconstruction from the trusted candidate/editor. No converter
silently infers an integer/date from a string or drops an absent historical
level.

Monitoring does not depend on `groupings.toml` at run time. Its frozen variants
inherit the exact grouping and level universe embedded in the deployed candidate.

## Governed source identity

Replace numeric filename-prefix filtering with semantic roles. The governed
model-source identity is a versioned canonical envelope, not a concatenation
whose composition is implicit. It contains the current
`IngestionSourceIdentity` SHA, `ModelDefinitionIdentity` SHA, canonical
`[validation]` identity, normalized governed training-code SHA, and the
model-kind extension described below. It also records (without folding locator
fields into semantic equivalence) the complete `ModelProjectBuildIdentity`.

The model run separately binds `IngestionBuildIdentity`, manifest, split, and
frame hashes. Dataset contents therefore create new data/run lineage without
pretending that byte-identical model source changed, while a stale frame can
never be paired with a newer ingestion-source identity.

The governed training-code SHA includes canonical content from:

- `sql/**/*.sql`;
- `model_spec.py`;
- `01_data_ingestion.ipynb` source cells;
- `03_model_training.ipynb` source cells; and
- every relative regular file listed in `[source].support_files`.

Configured support files use the same root-contained, no-symlink-escape
resolver as SQL. Duplicate paths, directories, globs, and files outside the
model root are rejected. Version 2 conservatively treats every configured
support file as capable of affecting both ingestion and model construction, so
it enters both identities. Introducing narrower semantic support-file roles
requires a later config-schema version rather than an implicit optimization.

Notebook cells carry stable semantic-role metadata. Every code cell in notebooks
01 and 03 is governed and hashed by default. The only exclusions are
package-owned, checksum-verified operational cells whose roles are limited to
display, credential acquisition, or the runtime `RemoteWriteCapability` prompt;
editing such a cell removes its exemption and either includes it in the digest
or blocks if it attempts to serialize authorization. Unknown or untagged custom
code is always included. Cell IDs/tags select a role but never substitute for
hashing source bytes. Execution state, entered prompt text, outputs, and
execution counts are excluded.

The semantic identity is model-kind aware. RAW binds the canonical raw model
contract and excludes grouping decisions. ROUTINE_EDIT includes the canonical
semantic digest of `groupings.toml` and the effective grouped-feature contract.
EDITOR_EDIT and MANUAL_EDIT inherit the parent model-source digest and add
their existing immutable submission or policy evidence. An absent grouping
file and a present semantic-empty grouping file share the same empty grouping
digest; because no ROUTINE_EDIT is created in either case, that equivalence
cannot erase a real grouped run.

Derived and deployment actions preserve two distinct locators: the parent's
original `ModelProjectBuildIdentity`, which remains the authority for fitted
semantics, and the current clean `ActionProjectIdentity`, which records the
company model-repository commit/lock that executed the editor, manual policy,
monitoring, or deployment action. The latter is audit lineage and does not
silently replace or re-hash the parent's source. Both are required for a new
remote write.

It excludes notebook outputs and the exploratory/editor/manual/deployment
notebooks (`02`, `04`, `05`, and `06`). Those steps create their own immutable
submission, policy, artifact, receipt, or deployment evidence. Tests assert
inclusion by role, never by numeric prefix.

## Scaffold safety and upgrades

Scaffold state is explicit and derived before any mutation:

- **UNINITIALIZED:** only the unmanaged `pyproject.toml`/`uv.lock` prerequisites
  and otherwise nonconflicting user files exist.
- **LEGACY:** no standalone marker exists and one complete known historical
  layout fingerprint is present.
- **MANUAL_PENDING:** a reviewed version-2 `pricing_model.toml` exists with
  `scaffold_state = "manual_pending"`, at least one customized legacy role is
  intentionally retained, no recovery journal exists, and a generated upgrade
  plan names every remaining action. Notebook/model write commands refuse this
  state; read-only extraction and `scaffold --upgrade` remain available.
- **RECOVERY_PENDING:** a valid unfinished upgrade journal exists. It takes
  precedence over all other observations, and only status plus the matching
  `--recover-old`/`--recover-new` action is legal.
- **CURRENT:** `scaffold_state = "current"`, the supported `template_version`,
  exact required role set, and every managed-file contract validate with no
  journal or legacy collision.
- **CONFLICTED:** every unknown, partial, multiply matched, or internally
  inconsistent layout. It is read-only until an analyst reconciles it.

The complete legal file-role sets and transition graph are versioned packaged
data, not scattered conditionals. `template_version` and `scaffold_state` are
excluded from fitted semantic identity but remain tracked audit state. A legacy
upgrade enters `MANUAL_PENDING` only through an explicit
`--accept-project-config` action after dry-run; merely discovering ambiguity
does not create a marker or change bytes. Only one journalled final transition
may set `CURRENT` and advance `template_version`.

### Initial scaffold

`pricing-pipeline scaffold` first verifies the pre-existing `pyproject.toml`
and `uv.lock`, then preflights the complete managed output tree before writing.
It rejects managed ancestor and leaf symlinks, absolute or escaping paths, and
conflicting existing files. Each new file is written to a same-filesystem
temporary and atomically installed. An identical retry is a true no-op,
including mtimes.

Before preflight, the command obtains an exclusive OS lock on a handle to the
validated target root (or its validated parent for an uncreated target). A
second scaffold/upgrade fails without mutation. All traversal and mutation use
directory-anchored, no-follow handles; the implementation revalidates directory
device/inode or Windows file identity before each operation and rejects reparse
points/symlink replacement. New destinations use atomic no-clobber creation,
not check-then-rename. Replacement is allowed only for a byte/inode fingerprint
captured under the same lock. Platforms without the required no-follow and
no-clobber primitives block mutation rather than weakening the guarantee.
Temporary files and every affected parent directory are fsynced before success
is reported.

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
  leaves it byte-for-byte unchanged, and requires the explicit
  `MANUAL_PENDING` transition before any other files may change;
- stages all replacement bytes and a journal before applying per-file atomic
  moves;
- aborts with zero changes on collisions, `CONFLICTED` layouts, symlinks, or
  unknown notebook roles; and
- never runs Git commands or moves a project into another repository.

A legacy layout with no marker requires an explicit reviewed
`--project-config <path>` containing every governed field. The upgrader may
extract suggestions from cells whose complete historical template fingerprint
is known, but it never treats suggestions as approved input. It stages the
reviewed config as `pricing_model.toml`, validates that `model_spec.py`, SQL,
roles, validation, and notebook managed cells agree with it, and keeps the
upgrade in `MANUAL_PENDING` until all required fields and digests validate.

Multi-file replacement cannot be crash-atomic. The guarantee is therefore:
complete preflight before mutation, per-file atomic replacement, journaled
backups, rollback for any caught in-process failure, and explicit crash
recovery. The journal and backups are fsynced before the first move. On a later
invocation, an unfinished journal blocks normal operation and offers verified
`--recover-old` or `--recover-new` completion. Tests inject failure before and
after every journalled move. The scaffold never claims success or advances the
marker version while recovery is pending. Every move is repeated through the
same anchored/no-follow helper, and each parent directory is fsynced before the
journal advances. Recovery verifies all expected old/new hashes and refuses to
guess if an external writer changed either side.

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
and `sql/model_data.sql` remain tracked. CI parses notebook JSON and requires
`outputs = []`, null execution counts, no cell attachments, no widget state, no
rich MIME payloads, and an allowlist-normalized metadata shape. Top-level
metadata is limited to normalized kernel/language identifiers; cell metadata is
limited to stable cell ID and reviewed semantic-role tags. Unknown metadata,
binary/base64 blobs, oversized opaque strings, and output-like MIME keys fail
closed rather than being stripped silently. The same scanner examines all
tracked paths for prohibited data/artifact patterns and secret signatures.
Fixtures place unique encoded sentinels in outputs, Markdown attachments,
widget state, top-level metadata, and cell metadata and prove each is rejected.
`.gitignore` is only a guardrail; confidential content must never enter
framework Git history.

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

The company reserves the PEP 440 local namespace
`<upstream-version>+company.<monotonic-build>` and tag namespace
`company/v<that-version>`. A tree-identical import uses the upstream version;
the first company-only descendant uses `+company.1`, and the counter never
reuses a version for a different tree. Company CI requires version, protected
tag, source commit, and attestation to agree and rejects a duplicate version
whose recorded tree SHA differs. When upstream advances its public version, the
company counter restarts only under that new base version.

### Model dependency

A model repository pins the complete company commit and commits its own lock:

```bash
uv add --no-sync \
  "airflow-superglm-builder[sqlserver,report,notebook] @ git+ssh://git@company.example/pricing/airflow_superglm_builder.git@<40-hex-company-commit>"
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

Define one immutable, versioned `FrameworkBuildIdentity` containing distribution
name, PEP 440 version, build kind (`GIT`, `WHEEL`, or `EDITABLE`), normalized
credential-free source-repository identifier, full 40-hex source commit,
protected release tag, build-attestation SHA-256, and signing-key ID. A Git
install obtains repository URL and commit from PEP 610 direct-reference metadata
and requires both to match an administrator-owned company-repository allowlist.
Company wheel CI embeds a signed build statement covering repository ID, source
commit, version, tag, and wheel build inputs; the model lock retains the wheel
archive hash. Verification uses a company trust store supplied by the runtime
module/host policy, never a key or allowlist controlled by the model repository.
An arbitrary fork, unverifiable wheel, editable install, or dirty framework tree
is marked untrusted and may explore locally but cannot make governed remote
writes. This check lives at the lowest shared remote-write boundary, not only in
notebook helpers.

Persist the complete framework and model-project identities in frame and
candidate artifact envelopes, publication receipts and lineage, monitoring
contracts, SQL Server model-run evidence, SQLite, and deployment views alongside
Python and SuperGLM versions. New successful governed runs require both trusted
identities. The first implementation migration adds nullable fields, labels old
evidence `LEGACY_UNKNOWN`, and uses triggers plus application validation to
require complete identities for new successful rows.

All artifact and receipt formats have explicit versions and immutable readers.
Legacy frame v1, candidate bundle v1/v2, grouping v1, and publication-receipt v1
fixtures remain loadable through adapters that preserve missing facts as
`LEGACY_UNKNOWN`; adapters never invent a framework, ingestion, or project
identity. Legacy artifacts may be listed, inspected, reported, and used to keep
an already-open deployment operational. They cannot become the parent of a new
editor/manual/monitoring publication, be newly deployed, or be republished
until an administrator attestation command has independently verified the
artifact and SQL receipt against an archived trusted framework/model revision.
If that proof is unavailable, the model must be rebuilt from a clean standalone
repository. Notebook 04–06 surfaces the restriction as an actionable state,
not a deserialization failure.

### Migration identity and compatibility

Every framework release ships a canonical ordered migration manifest for each
backend. Each entry records ordinal, filename, SHA-256 of normalized packaged
source bytes (`source_sha256`), schema API version after application, minimum
required migration, compatible writer API range, and release-manifest ID. A
company schema-release attestation signs the complete manifest, framework
repository ID/commit/version, compatibility range, and signing-key ID.

The company signature is required to authorize remote SQL Server writes and to
trust migrations unknown to an older client. A personal/upstream or editable
build may still create and mutate a disposable local SQLite database when every
migration is present in that exact installed package and its source checksum
matches; status records trust scope `LOCAL_ONLY`. Such a database/build can
never authorize a remote write or treat an unknown `AHEAD` chain as compatible.

SQL Server schema-name rendering has a separate checksum domain. Before
execution, the command records a canonical schema-mapping SHA and SHA-256 of the
exact rendered SQL bytes (`rendered_sha256`). The database migration row stores
both source and rendered hashes plus the mapping hash; status verifies packaged
source first, renders with the recorded mapping, then verifies the executed
domain. Existing rows that contain only the historical rendered checksum are
backfilled only when the known packaged source, legacy renderer, mapping, and
stored checksum all reproduce exactly. Otherwise status is
`CHECKSUM_MISMATCH`; no checksum is guessed or rewritten.

The database records schema API version separately from migration ordinal and
stores each signed release manifest under DDL-owner permissions. Additive,
backward-compatible migrations retain the API version; a migration that breaks
older writers increments it. Schema status validates the complete applied set,
not merely the greatest filename:

- **UNINITIALIZED:** tracking table absent. Status and guarded apply/reset are
  available; governed writes are blocked.
- **BEHIND:** applied rows are an exact checksum-valid prefix of the packaged
  chain. Status and apply are available. Governed writes are allowed only when
  the database API version is supported and the framework's minimum required
  migration has been reached.
- **CURRENT:** the complete packaged chain and release attestation match and the
  API version is supported. Governed writes are allowed.
- **AHEAD_COMPATIBLE:** the packaged prefix matches; every later row belongs to
  a complete schema-release manifest whose company signature validates against
  the host trust store; and that attestation explicitly includes this client's
  writer API version. Governed writes are allowed, enabling staggered model-repo
  upgrades.
- **AHEAD_INCOMPATIBLE** or **AHEAD_UNTRUSTED:** the later attestation excludes
  this writer API, is incomplete, or cannot be authenticated. Reads/status
  remain available and governed writes block.
- **DIVERGED:** missing/interleaved filenames or non-prefix history. Status and
  destructive reset dry-run remain available; apply and governed writes block.
- **CHECKSUM_MISMATCH** or **FAILED:** any known checksum differs or the tracker
  records a failed/incomplete application. Only status and explicitly confirmed
  disposable reset remain available.
- **NONCANONICAL:** development SQL resources were used. Remote governed writes
  always block until a packaged-resource reset.

Apply is transactional and inserts its migration row, release manifest, and API
version only after the SQL succeeds. A signed `AHEAD_COMPATIBLE` attestation is
the trust mechanism for staggered upgrades; a bare future filename or claimed
API integer is never enough.

### SQLite migration parity

SQLite uses its own packaged, append-only migration directory and canonical
manifest with the same API/status vocabulary; it does not keep replaying a
monolithic bootstrap followed by ad hoc Python alterations. Fresh databases run
the chain from V001. Existing local databases enter a one-time adoption path
that fingerprints every table, index, trigger, view, attachment, and relevant
pragma against a finite set of supported legacy schemas, records the matching
baseline, and then runs later migrations. Unknown or orphaned structures become
`DIVERGED` and are never silently normalized.

One migration ledger in the governed `pricing` database covers the coordinated
`main`, `pricing`, `pricing_stg`, and `mlops` attachments. A migration runs under
an exclusive lock and one rollback-journal transaction across validated distinct
files; WAL/memory arrangements that cannot provide the required coordinated
guarantee are rejected. `PRAGMA foreign_keys=ON` and a full qualified
`foreign_key_check` execute before commit. A fsynced recovery marker records the
old/new manifest and file identities so an interruption cannot be mistaken for
success; recovery either verifies the fully old state or completes/verifies the
fully new state. The ledger row and API version commit with the DDL. SQLite
`schema status`, `apply`, compatibility preflight, reset, and test fixtures cover
the same `BEHIND`, `CURRENT`, trusted/incompatible `AHEAD`, divergence, checksum,
failure, and noncanonical behavior as SQL Server.

Notebook connection preflight reports:

- verified framework repository, version, full commit, release attestation, and
  trust status;
- verified model-project repository, clean commit, lock SHA, governed source
  SHA, and any `LOCAL_UNBOUND` reason;
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
- From the built wheel in a temporary Git repository, execute a fully synthetic
  standalone 01 ingestion -> optional 02 grouping -> 03 RAW/ROUTINE publication
  -> package inspection -> deployment flow against fresh SQLite. The smoke must
  not import any framework-checkout path.

### Standalone scaffold

- Scaffold into an empty external directory and assert the exact golden tree,
  strict config, notebook names/order, sanitized notebook JSON, and no
  `sys.path` mutation.
- Execute/compile notebook setup cells using only site-packages.
- Cover every versioned TOML validation variant, default, cross-field rejection,
  legacy adapter, and unknown-newer-version failure.
- Verify marker discovery from root and descendants and reject invalid,
  escaping, symlinked, or ambiguous roots.
- Assert notebook 01 reads exactly `sql/model_data.sql` through `pathlib` and
  SQLAlchemy bind parameters.
- Validate idempotent retry, dry-run, state transitions, exclusive-lock
  contention, ancestor/leaf replacement races, atomic failure, directory fsync,
  customized-file preservation, every legacy mapping, recovery at every move,
  and exact no-change-on-conflict.

### Groupings and governed identity

- Cover empty, existing, editor-created, multiple-feature, multiple-group,
  typed-level, overlap, new-level, missing-historical-level, and version-upgrade
  cases.
- Prove the generated Joblib object matches canonical TOML semantics and is
  rejected after byte, frame, provenance, or runtime tampering.
- Freeze legacy grouping artifacts with string/int/date ambiguity, absent
  historical levels, and missing base/order/special facts; prove automatic
  promotion blocks unless trusted sources make every identity exact, and prove
  review templates are never accepted as governed config.
- Prove notebook 02 performs no SQL write and notebook 03 is the first model
  publication step.
- Prove a frame created by notebook 01 is rejected by notebooks 02/03 after any
  ingestion SQL, config, bind-parameter, support-file, or notebook-01 source
  change, while an unrelated commit with byte-identical ingestion source remains
  valid.
- Prove source hashes change for governed config/SQL/01/03/supporting code and
  do not change for 02/04/05/06 or notebook outputs.
- Prove every sample/export-weight and offset-role change alters both RAW and
  ROUTINE_EDIT source identity.
- Prove changing only `groupings.toml` leaves RAW identity unchanged, changes
  ROUTINE_EDIT identity, and invalidates an exploration grouping handoff whose
  recorded model-definition/grouping digest no longer matches.
- Prove family/link/Tweedie power, basis, knot, smoothing, monotonic, interaction,
  penalty, and fit-control changes alter the canonical model contract even when
  file names and feature names do not.

### Schema and legacy compatibility

- Exercise fresh and every supported legacy SQL Server migration chain against a
  real disposable SQL Server in release CI; static batch splitting alone is not
  sufficient.
- Exercise fresh and legacy multi-file SQLite adoption, transactional failure,
  crash recovery, foreign-key checks, and status parity.
- Prove raw/rendered/schema-mapping checksum domains and legacy checksum backfill
  with non-default SQL schema names.
- Cover `BEHIND`, `CURRENT`, signed `AHEAD_COMPATIBLE`, incompatible/untrusted
  `AHEAD`, divergence, checksum mismatch, failure, and noncanonical resources on
  both backends. An unsigned future migration must never authorize writes.
- Keep immutable v1/v2 frame, grouping, candidate, and publication fixtures;
  prove allowed inspection and prohibited child/deployment operations for
  `LEGACY_UNKNOWN`.

### Release and confidentiality

- Test version/tag/repository/source-SHA/attestation equality and propagate the
  complete mandatory framework and model-project build identities through frame,
  artifact, publication, monitoring, deployment, SQL Server, and SQLite evidence.
- Reject remote writes from a dirty model repository, uncommitted lock, wrong
  company framework commit, forked repository URL, unverifiable wheel, editable
  install, and clean source whose lock SHA changed. Confirm these states still
  allow local exploration.
- Use `git check-ignore` assertions for every generated sensitive artifact type
  while proving SQL/config/notebooks remain trackable.
- Reject unique sentinels in every notebook output, attachment, widget/rich MIME,
  top-level metadata, and cell-metadata location, including encoded payloads.
- Run existing full SQL migration, SQLite, publication, deployment, manual-edit,
  monitoring, reporting, notebook, and confidentiality suites.

## Delivery sequence

1. **Identity foundation:** normative config and artifact versions,
   `IngestionBuildIdentity`, `ModelDefinitionIdentity`, framework/model-project
   build identities, trust-store interface, and frozen legacy fixtures.
2. **Package foundation:** build backend, `src` layout, version source,
   packaged SQL/templates, clean-room wheel tests.
3. **CLI:** common parser, scaffold/schema/inspect/report commands, module entry,
   compatibility wrappers.
4. **Standalone project:** root marker/config, model tree, SQL loading, new
   notebook order, role-based source hashing, confidentiality defaults.
5. **Grouping bridge:** tracked TOML, exploration compiler/editor export,
   generated Joblib, notebook 03 consumption.
6. **Safe upgrade:** dry-run, template fingerprints, journalled legacy notebook
   migration/recovery, operator guide for extracting model repositories.
7. **Governance:** dual-domain SQL checksums, signed compatibility preflight,
   versioned SQLite migrations, identity persistence, and legacy readers.
8. **Release:** company import runbook, immutable tag/commit validation, example
   standalone model repository smoke test.

Each delivery step ends with its focused tests and a clean-room installed-wheel
smoke. The final release requires the entire existing suite plus the new
standalone-consumer suite.

## Acceptance criteria

The design is complete when all of the following are true:

1. From an empty directory outside this checkout, a user can install the
   company-pinned framework and run `uv run pricing-pipeline scaffold ...`.
2. The generated model repository has exactly the six numbered notebooks and
   contains `pricing_model.toml`, `model_spec.py`, optional `groupings.toml`,
   `sql/model_data.sql`, and the documented support files—without a copied
   framework package or nested model directory.
3. Generated notebooks import only the installed library and work from any cwd
   inside the model repository.
4. Notebook 02 supports no grouping or existing grouping input and can export
   reviewed decisions without a published RAW package.
5. Notebook 03 publishes RAW and optional ROUTINE_EDIT models with full manifest,
   data-as-at, ingestion, grouping, split, framework, model-project, lock,
   Python, and SuperGLM evidence; it cannot publish a stale frame.
6. Schema and SQLite commands use installed package resources by default;
   explicit development overrides are isolated and separately tested.
7. Scaffold retry and upgrade never overwrite customized files or follow
   symlinks; explicit states and one exclusive lock govern transitions; writes
   are no-clobber/per-file atomic, caught failures roll back, and crashes leave a
   mandatory recoverable journal rather than a false success.
8. Model source hashing follows semantic roles rather than numeric filename
   prefixes.
9. A model repository is reproducible from its tracked source and `uv.lock`
   without the framework checkout, and every remote publication points to its
   clean protected company commit and exact lock digest.
10. No work model, query, data, artifact, credential, or work-only change can be
    pushed through the configured personal remote, and first-push/import checks
    cover every reachable Git ref rather than only the current tree.
11. SQL Server and SQLite report the same versioned compatibility states; only
    packaged or signed-compatible migrations can authorize governed writes.
12. Legacy artifacts remain inspectable without fabricated provenance and
    cannot silently become parents of new governed evidence.
