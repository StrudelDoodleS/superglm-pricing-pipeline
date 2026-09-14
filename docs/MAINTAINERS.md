# Maintainer map

Start with [How the package fits together](package-flows.md) to follow objects
between operations. For a CLI option, use the [argument-to-notebook trace](scaffold-trace.md).
The [module index](module-index.md) links every Python file to its purpose.
The [developer usability audit](dev-ux-audit.md) records remaining structural issues.

Select **Pricing developer** in Copilot to follow these maps while working on
the package. Its instructions are in
[`.github/agents/pricing-developer.agent.md`](../.github/agents/pricing-developer.agent.md).
It reads the relevant guide and follows the owner, caller and tests for the task.

The canonical agent is shipped in
[`resources/scaffold/pricing-developer.agent.md`](../src/pricing_pipeline/resources/scaffold/pricing-developer.agent.md).
Keep the repository copy in sync when editing it. `pricing-pipeline init` seeds
it alongside Pricing builder and preserves customized copies. The developer
guides require the framework source checkout; they are not copied into analyst projects.

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
| Scheduled execution | No installed scheduler command | external runners can call the library API | [Current call flows](package-flows.md) |
| Reporting | documented reporting API | `reporting/` | [Notebook API](notebooks/README.md) |
| Scratch experiments | optional, never governed or published | `modeling/scratch_*` | [Notebook API](notebooks/README.md) |

## Change boundaries

- Keep `pricing_pipeline.notebook` and the installed CLI small and stable.
- Scaffold config parses values, rendering creates notebook text, and the
  filesystem service writes it. Do not mix those responsibilities.
- SQL migrations are immutable after release. Add a migration; never edit a
  deployed one.
- Keep schema apply and reset in the administrator scripts. Shared SQL schemas
  can contain several projects; do not add these operations to the analyst CLI
  or run them automatically from notebooks.
- Scheduled work calls existing operations. It does not reimplement fitting,
  lineage, publication, or persistence.
- Reporting and scratch helpers do not control governed model lifecycle state.

## Direct execution traces

```text
Generic report:
  reporting.build_scored_model_report
  -> reporting.report.build_scored_model_report
  -> reporting.inputs.normalize_report_inputs
  -> reporting.evidence.collect_model_evidence
  -> reporting.diagnostics.calculate_diagnostics
  -> reporting._underwriter_html.render_underwriter_html

Convenience report:
  reporting.build_underwriter_report
  -> reporting.report.build_underwriter_report
  -> optional evidence adapters
  -> the generic report path above

Scaffold:
  cli.main
  -> scaffold.commands
  -> scaffold.config.resolve_scaffold_options
  -> scaffold.service.scaffold_resolved_pricing_model
  -> scaffold.render and packaged notebook resources
```

The final reporting owners are `reporting.inputs` for input contracts and
normalization, `reporting.evidence_types` for adapter records,
`reporting.evidence` for collection and normalization, `reporting.movement`
for movement calculations, `reporting.diagnostics` for diagnostic assembly,
and `reporting.report` for both supported workflows. The HTML and style modules
render only and are intentionally excluded from functional-flow simplification.

## Lifecycle ownership

| Transition | Owner |
|---|---|
| source data -> verified frame and manifest | `data/`, `pricing_pipeline.notebook` |
| manifest -> fitted candidate | `modeling/standard_superglm.py` |
| candidate -> immutable published package | `publishing/publish.py`, `publishing/sqlserver.py`, `publishing/sqlite.py` |
| published package -> editor/manual child | `workbench/`, `publishing/editor.py`, `modeling/manual_adjustment.py` |
| published package -> deployment | `publishing/deployment.py` |
| deployment -> monitoring evidence | `modeling/monitoring/workflow.py`, `modeling/monitoring/persistence.py` |
| schema version -> migrated/seeded/reset database | `infra/`, packaged SQL resources |

## Publication module map

The supported boundary is `pricing_pipeline.notebook`; the publishing
modules own the implementation. `editor.py` also re-exports its existing public
records and helpers; their definitions live with the stages below:

| Module | Purpose |
|---|---|
| `publish.py` | immutable request, common validation, backend dispatch, and publication result types |
| `identity.py` | identifiers, equivalence fingerprints, conflict comparison, and equivalent-publication lookup |
| `rating_tables.py` | workbook export/parsing, normalized rating frames, and canonical content hashes |
| `metadata.py` | SuperGLM receipt models, canonical receipt bytes, and term metadata extraction |
| `lineage.py` | durable model-run, dataset, split, metric, fold, and parent evidence |
| `sqlserver.py` | SQL Server registration, version reservation, locking, package transaction, and persisted parity verification |
| `sqlite.py` | local registration, version reservation, locking, package transaction, and local audit lineage |
| `editor.py` | publication workflow, artifact attempt cleanup and request construction |
| `editor_contracts.py` | parent, export and publication records; submission identity helpers |
| `editor_parent.py` | verify and load parent data, artifacts and champion evidence |
| `editor_replay.py` | replay edits and verify fitted-model state and manual policies |
| `editor_export.py` | write the child build and comparison metrics |
| `editor_retry.py` | verify existing or equivalent publications against stored lineage |
| `deployment.py` | explicit deployment transition and stale-champion protection |
| `recipes.py` | automatic recipe revisions, model locking, and verification of reused recipe content |
| `spline_segments.py` | polynomial coefficients, interval bounds, and tail validation for exact spline export |

Every RAW, ROUTINE_EDIT, EDITOR_EDIT, and MANUAL_EDIT publication follows one
linear sequence:

```text
ApprovedModelBuild
-> PublicationRequest
-> validate immutable artifacts and identity
-> prepare RatingTables and canonical digests once
-> resolve exact retry or semantic equivalent
-> run one concrete SQLite or SQL Server transaction
-> write package and lineage
-> verify persisted output
-> return CompletedModelPublishResult
```

## Test lanes

Focused scaffold work:

```bash
uv run python -m pytest -q tests/test_scaffold_pricing_model.py tests/cli/test_init_and_scaffold.py
```

Monitoring:

```bash
uv run python -m pytest -q tests/test_model_monitoring.py tests/test_monitoring_simulation.py tests/test_monitoring_data_checks.py tests/test_monitoring_support_checks.py
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

Cross-domain integration:

```bash
uv run python -m pytest -q tests/test_notebook_workflow.py tests/test_offline_sqlite.py tests/test_model_monitoring.py
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
