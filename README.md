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

Use your Git host, team, and repository in the dependency URL.
The plain-Python fallback, which only works after installation, is:

```bash
python -m pricing_pipeline init
# edit pricing_scaffold.toml
python -m pricing_pipeline scaffold \
  --model-name CLAIM_FREQUENCY \
  --target-name claim_count
```

`init` and a local scaffold do not require uv. The model repository owns `ipykernel`;
a private runtime package owns SQL driver and authentication dependencies.

The installed command is `pricing-pipeline`, with a hyphen. It exposes
`init` and `scaffold`. Commands below that use `python scripts/...` require
a checkout of this package repository; installing the dependency does not add
those scripts to your model project.

`runtime_module` is the installed private Python module that exposes
`get_engine(database=None)`. The TOML contains no credentials: keep them in
that module's secret provider.

The scaffold creates six notebooks under `pricing_models/claim_frequency/`:

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

`init` seeds **Pricing builder** and **Pricing developer** under `.github/agents/`.
Rerunning it adds missing agents and preserves config and agent edits. For package
maintenance, the developer agent uses the [source navigation guides](docs/MAINTAINERS.md).

The source checkout wrapper `scripts/scaffold_pricing_model.py` invokes the same scaffold.

## Important rules

- Data-as-at is dataset identity, not a fit or deployment timestamp.
- Grouping happens in Python; SQL stores the completed model and evidence.
- Equivalent successful models are detected before SQL staging.
- Local mode uses persistent SQLite audit databases; guarded remote mode is
  required for editor/manual publication and deployment.
- Save notebooks before building: source cells are evidence, while outputs and
  execution counts are not.

## Guides

- [Runnable freMTPL frequency demo](tutorials/fremtpl_frequency/demo.ipynb),
  with [setup and terminal instructions](tutorials/README.md).
- [Grouped model recipes and challenger comparison](tutorials/model_recipes/comparison.ipynb)
- [Notebook workflow and function reference](docs/notebooks/README.md)
- [SQL schema, relationships, triggers, views, and migration runbook](docs/sql/README.md)
- [Script command index](scripts/README.md)
- [Developer guide: package flows, module owners and argument-to-notebook mapping](docs/MAINTAINERS.md)

To compare already-scored models, run `scripts/build_underwriter_report.py`
from a package source checkout with
`docs/notebooks/underwriter_report.example.toml`. It creates one offline HTML
file and does not write models or diagnostics to SQL.

The packaged `pricing_pipeline.resources.migrations` chain is the authoritative
SQL Server schema; inspect it with `pricing_pipeline.resources.migration_root()`
and do not copy runnable DDL.

## Database administration

Schema migrations and resets are administrator operations run from the package
repository. They are deliberately excluded from the analyst CLI because the
database schemas can contain models from multiple projects.

To apply only missing migrations and retain existing data, run:

```bash
uv run python scripts/apply_schema.py \
  --runtime-module project_runtime.database \
  --expected-database PricingAudit
```

The destructive reset command and safeguards are in the [SQL
runbook](docs/sql/README.md).

## Verify the package from a source checkout

```bash
uv sync --locked --all-extras
uv run --locked --all-extras python -m pytest -p no:cacheprovider -q
uv build --force-pep517 --sdist --wheel --out-dir dist
```

Only `tests/packaging/test_clean_wheel_install.py` proves the built wheel works
outside this checkout. Do not commit model-local `.local/` state, notebook
outputs, credentials, or runtime modules containing credentials.

Export with `candidate.recipe.save(path)`; reload with `ModelRecipe.load(path).build(dataset=dataset)`.
SQL assigns recipe revisions on save. Deployment is separate. The database
administrator must apply V047 and V048 before models are saved with this version.
