# Maintainer map

The package has four jobs:

```text
library API -> database lifecycle -> SQL/Power BI
      |                 ^
      v                 |
workspace scaffold -> scheduled execution
```

| Capability | Supported entry point | Implementation | Detail |
|---|---|---|---|
| Library API | `pricing_pipeline.notebook` | `data/`, `modeling/`, `publishing/`, `workbench/` | [Notebook API](notebooks/README.md) |
| Database lifecycle | packaged migrations and guarded scripts | `infra/`, `resources/migrations/`, `resources/offline_sqlite/` | [SQL schema](sql/README.md) |
| Workspace scaffold | `pricing-pipeline init`, `pricing-pipeline scaffold` | `cli.py`, `scaffold/`, `resources/scaffold/` | [Notebook workflow](notebooks/README.md) |
| Scheduled execution | future `pricing-pipeline weekly` | must compose the public library API | [Architecture](architecture/maintainability-consolidation.md) |
| Reporting | documented reporting API | `reporting/` | [Notebook API](notebooks/README.md) |
| Scratch experiments | optional, never governed or published | `modeling/scratch_*` | [Notebook API](notebooks/README.md) |

## Change boundaries

- Keep `pricing_pipeline.notebook` and the installed CLI small and stable.
- Scaffold config parses values, rendering creates notebook text, and the
  filesystem service writes it. Do not mix those responsibilities.
- SQL migrations are immutable after release. Add a migration; never edit a
  deployed one.
- Scheduled work calls existing operations. It does not reimplement fitting,
  lineage, publication, or persistence.
- Reporting and scratch helpers do not control governed model lifecycle state.

## Lifecycle ownership

| Transition | Owner |
|---|---|
| source data -> verified frame and manifest | `data/`, `pricing_pipeline.notebook` |
| manifest -> fitted candidate | `modeling/standard_superglm.py` |
| candidate -> immutable published package | `publishing/`, `orchestration/pipeline.py` |
| published package -> editor/manual child | `workbench/`, `publishing/editor_candidate.py`, `modeling/manual_adjustment.py` |
| published package -> deployment | `publishing/deployment.py` |
| deployment -> monitoring evidence | `modeling/monitoring.py` |
| schema version -> migrated/seeded/reset database | `infra/`, packaged SQL resources |

## Test lanes

Focused scaffold work:

```bash
uv run python -m pytest -q tests/test_scaffold_pricing_model.py tests/cli/test_init_and_scaffold.py
```

Monitoring:

```bash
uv run python -m pytest -q tests/test_model_monitoring.py tests/test_monitoring_simulation.py
```

Publishing:

```bash
uv run python -m pytest -q tests/test_rating_export.py tests/test_package_writer.py tests/test_local_model_equivalence.py
```

Reporting:

```bash
uv run python -m pytest -q tests/test_underwriter_report.py tests/test_superglm_report_adapter.py
```

SQL lifecycle:

```bash
uv run python -m pytest -q tests/test_migrations.py tests/test_offline_sqlite.py tests/test_packaged_resources.py
```

Release gate:

```bash
uv lock --check
uv run --locked --all-extras python -m pytest -q
git diff --name-only --diff-filter=ACMR origin/main...HEAD -- '*.py' |
  xargs -r uv run ruff check
git diff --name-only --diff-filter=ACMR origin/main...HEAD -- '*.py' |
  xargs -r uv run ruff format --check
uv build
uv run python -m pytest -q tests/packaging
git diff --check
```

Use the focused lane while editing. Run the release lane once before merging.
The repository still has inherited Ruff debt outside the changed-file gate; do
not mix mechanical whole-repository cleanup into a domain change.

## Confidentiality

Never commit source datasets, model-frame artifacts, fitted models, row-level
predictions, credentials, environment dumps, or generated state. Keep local
and SharePoint-synced artifacts outside Git. Package tests must inspect archive
contents before release. Never log or embed row-level values, raw predictions,
comparison-unit identifiers, credentials, or source data in HTML or SQL
evidence; persist only approved aggregate evidence.
