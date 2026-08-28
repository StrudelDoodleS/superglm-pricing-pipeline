# SuperGLM pricing pipeline

This package provides a notebook-first path from model data to a reviewed,
immutable SQL rating package.

## Start a model repository

```bash
uv init --bare --python 3.14
uv add "superglm-pricing-pipeline @ git+ssh://git@HOST/TEAM/REPOSITORY.git@v0.2.1"
uv run pricing-pipeline init
# edit pricing_scaffold.toml
uv run pricing-pipeline scaffold \
  --model-name CLAIM_FREQUENCY \
  --target-name claim_count
uv add --dev ipykernel
```

Use the real internal Git host, team, and repository in the dependency URL.
The plain-Python fallback, which only works after installation, is:

```bash
python -m pricing_pipeline init
python -m pricing_pipeline scaffold \
  --model-name CLAIM_FREQUENCY \
  --target-name claim_count
```

`init` and a local scaffold do not require uv. The model repository owns `ipykernel`;
a private runtime package owns SQL driver and authentication dependencies.

`runtime_module` is the installed private Python module that exposes
`get_engine(database=None)`. The TOML contains no credentials: keep them in
that module's secret provider.

The scaffold creates:

```text
pricing_models/claim_frequency/
├── 01_data_ingestion.ipynb
├── 02_model_exploration.ipynb
├── 03_model_training.ipynb
├── 04_model_editor.ipynb
├── 05_manual_adjustment.ipynb
└── 06_model_deployment.ipynb
```

| Notebook | Purpose |
|---|---|
| `01_data_ingestion.ipynb` | Build the governed model frame and record its Data-as-at date. |
| `02_model_exploration.ipynb` | Explore features, benchmarks, and groupings without publishing or deploying. |
| `03_model_training.ipynb` | Fit and publish `RAW`, then optionally `ROUTINE_EDIT`. |
| `04_model_editor.ipynb` | Optionally publish an `EDITOR_EDIT`. |
| `05_manual_adjustment.ipynb` | Apply replayable business factors and optionally deploy a `MANUAL_EDIT`. |
| `06_model_deployment.ipynb` | Review and deploy one selected package. |

`pricing_scaffold.toml` supplies connection names and safe notebook defaults.
An explicit `--config` wins, and explicit command-line options win over the
file. `ALLOW_REMOTE_WRITES` is deliberately not configurable; generated
notebooks set it to `False`.

For a legacy checkout command from a source checkout, copy
`pricing_scaffold.example.toml` to `pricing_scaffold.toml`; `uv run python
scripts/scaffold_pricing_model.py` calls the same installed scaffold command
with the same model and target options.

## Important rules

- Data-as-at is dataset identity, not a fit or deployment timestamp.
- Grouping happens in Python; SQL stores the completed model and evidence.
- Equivalent successful models are detected before SQL staging.
- Local mode uses persistent SQLite audit databases; guarded remote mode is
  required for editor/manual publication and deployment.
- Save notebooks before building: source cells are evidence, while outputs and
  execution counts are not.

Generated model repositories own their notebooks, data, configuration, and local
artifacts. This framework repository contains only the reusable Python package,
schema resources, documentation, and development tooling.

## Guides

- [Notebook workflow and function reference](docs/notebooks/README.md)
- [SQL schema, relationships, triggers, views, and migration runbook](docs/sql/README.md)
- [Script command index](scripts/README.md)

For an underwriter comparison of already-scored models, use
`scripts/build_underwriter_report.py` with
`docs/notebooks/underwriter_report.example.toml`. It creates one offline HTML
file and does not write models or diagnostics to SQL.

The packaged `pricing_pipeline.resources.migrations` chain is the authoritative
SQL Server schema; inspect it with `pricing_pipeline.resources.migration_root()`
and do not copy runnable DDL.

## Work database setup

Apply only missing migrations to an existing database:

```bash
uv run python scripts/apply_schema.py \
  --runtime-module work_runtime.database \
  --expected-database PricingAudit
```

The destructive reset command and safeguards are in the [SQL
runbook](docs/sql/README.md).

## Verify

```bash
uv sync --locked --all-extras
uv run --locked --all-extras python -m pytest -p no:cacheprovider -q
uv build --force-pep517 --sdist --wheel --out-dir dist
```

Only `tests/packaging/test_clean_wheel_install.py` proves the built wheel works
outside this checkout. Do not commit model-local `.local/` state, notebook
outputs, credentials, or private work runtime modules.
