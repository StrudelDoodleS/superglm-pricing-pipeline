# Maintainability Consolidation Design

**Date:** 2026-08-27
**Baseline:** `superglm-pricing-pipeline` v0.2.1

## Purpose

Make the installed pricing pipeline understandable and safely changeable by a
small team without removing its model-governance guarantees. This is a
behaviour-preserving consolidation, not a rewrite and not a feature release.

The current analyst workflow is already the product contract:

```text
install -> init -> scaffold -> ingest -> explore -> train -> review -> deploy
                                                   |
                                      weekly governed monitoring evidence
                                                   |
                                              SQL -> Power BI
```

The problem is internal legibility. Important behaviours are spread across
large modules, and the six generated notebooks are embedded cell-by-cell in a
single Python file. A maintainer should not need to understand reporting,
publishing, SQL persistence, and notebook JSON generation to make one local
change.

## Non-negotiable compatibility contract

Every consolidation slice preserves:

- the installed distribution and import name;
- the `pricing-pipeline` and `python -m pricing_pipeline` entry points;
- all documented exports from `pricing_pipeline.notebook`;
- the v0.2.1 `init` and `scaffold` arguments, return codes, and error classes;
- the six canonical notebook filenames and their generated JSON, source cells,
  metadata, and default values;
- model-source hashing, manifest identity, data-as-of semantics, grouping
  artifacts, candidate equivalence, publication, deployment, and monitoring
  semantics;
- all packaged SQL migration and SQLite resource bytes;
- SQL schemas, tables, views, triggers, and stored procedures;
- clean-wheel installation from an unrelated working directory; and
- existing confidentiality boundaries and ignored state/artifact paths.

No slice may add a runtime dependency, SQL migration, new user configuration,
automatic publication, or automatic deployment. If exact output must change,
that change leaves this consolidation and receives its own design.

Parity means observable v0.2.1 behaviour is unchanged. The refactor does not
reinterpret, improve, or broaden an existing contract while moving it.

## Chosen approach

Keep one installable distribution and reorganize it internally. Do not split
reporting or scratch utilities into independently versioned packages yet. Do
not rewrite the pipeline or replace the notebook workflow with a declarative
platform.

This retains one version and one installation command while creating explicit
internal boundaries. Optional dependencies continue to keep reporting,
scratch, notebook, and SQL Server integrations out of installations that do
not request them.

## Product capability map

The package has four primary responsibilities. This is the first architecture
view a maintainer should see:

```text
1. Library API
   model data, fitting, grouping, publication, deployment, monitoring evidence

2. Database lifecycle
   packaged schema migrations, canonical seed data, status checks, guarded reset

3. Workspace scaffold
   initialize configuration and create the standard notebook workspace

4. Scheduled execution support
   run approved non-manual steps and persist evidence for SQL/Power BI
```

Reporting is an optional consumer of the library API and SQL evidence, not a
fifth model-lifecycle system. Scratch benchmarks are experimental helpers, not
part of the governed production path.

The existing `data`, `modeling`, `publishing`, and `workbench` packages are
implementation details of the library API. They must have focused internal
boundaries, but analysts should not have to compose them directly. The
`pricing_pipeline.notebook` facade remains their supported entry point.

Database lifecycle commands and schema resources form one boundary even when
their implementation uses several schemas. Scaffold rendering does not own
database behaviour. Scheduled execution composes public library operations; it
does not duplicate ingestion, fitting, publication, or persistence logic.

The weekly scheduler command is designed only after the first consolidation
slices, but its boundary is fixed now: a small executor around governed public
operations, optionally using Papermill for model-specific ingestion, with SQL
as the monitoring record and Power BI as the monitoring interface.

## Supported surface

The public analyst surface is deliberately small:

1. `pricing-pipeline init` and `pricing-pipeline scaffold`;
2. documented functions re-exported by `pricing_pipeline.notebook`;
3. documented reporting entry points;
4. packaged migrations and maintained SQL views; and
5. the six generated notebook files.

Everything else is internal unless explicitly documented. Internal modules may
move without deprecation, but compatibility facades remain wherever existing
repository code or installed consumers import an established path.

## Target package map

```text
pricing_pipeline/
  cli.py                    installed command parser only
  notebook.py               stable notebook facade only
  scaffold/
    config.py               TOML parsing and validated options
    render.py               token validation and deterministic rendering
    service.py              safe filesystem creation and upgrade handling
    legacy.py               temporary compatibility re-exports
  resources/scaffold/
    pricing_scaffold.toml
    notebooks/
      01_data_ingestion.ipynb
      02_model_exploration.ipynb
      03_model_training.ipynb
      04_model_editor.ipynb
      05_manual_adjustment.ipynb
      06_model_deployment.ipynb
  modeling/monitoring/
    __init__.py             compatibility and public re-exports
    contracts.py            immutable contracts, variants, canonical identity
    fitting.py              score/refit variants and invariant verification
    evidence.py             terms, lambdas, relativities, metrics, digests
    persistence.py          SQL lineage validation and idempotent persistence
    api.py                  thin orchestration of the preceding units
```

Publishing and reporting remain in their current packages during the first two
slices. Their large modules receive separate consolidation designs only after
the scaffold and monitoring boundaries prove the method.

## Slice 1: scaffold extraction

Move each notebook body into an installed notebook resource. A notebook
resource is valid notebook JSON containing a small, documented set of template
tokens. It is readable directly in Jupyter or a text editor.

The renderer:

1. loads the exact six resources through `importlib.resources`;
2. validates the expected resource names and token set;
3. replaces typed values recursively without evaluating template text;
4. rejects unknown or unresolved tokens;
5. emits deterministic JSON with the existing formatting; and
6. returns filename-to-text values to the filesystem service.

Configuration parsing contains no notebook bodies or filesystem writes. The
filesystem service contains no notebook-cell definitions or TOML parsing. It
retains the current ancestor/leaf symlink checks, no-follow writes, collision
handling, legacy deployment-notebook migration, and `--force` semantics.

The existing `scaffold.legacy` module becomes a thin compatibility facade for
one release. New code imports the focused modules.

Acceptance criteria:

- every v0.2.1 scaffold contract test passes unchanged;
- a golden test compares every generated notebook byte-for-byte with the
  v0.2.1 output for representative local and remote configurations;
- the installed wheel contains exactly the six templates and no generated
  model workspace;
- `legacy.py` contains no notebook cell body and is below 250 lines; and
- each new scaffold module has one stated responsibility and remains below
  500 lines, excluding data-only notebook resources.

## Slice 2: monitoring separation

Convert `modeling/monitoring.py` into a package while preserving imports from
`pricing_pipeline.modeling.monitoring` and all re-exports from
`pricing_pipeline.notebook`.

Responsibilities are separated as follows:

- **contracts** owns immutable dataclasses, enums, typed categorical identity,
  canonical serialization, and schema-version constants;
- **fitting** owns exact candidate reload/binding, variant execution, frozen
  structure/lambda/knot guards, and materialized fitted variants;
- **evidence** owns extraction and normalization of terms, lambdas,
  relativities, metrics, and complete-result digests;
- **persistence** owns manifest/deployment/run lineage checks, SQL statements,
  idempotent retry resolution, and immutable evidence writes; and
- **api** validates the high-level request and composes those units.

Fitting must not issue SQL writes. Persistence must not refit or mutate a
model. Evidence extraction must not open database connections. Contracts must
not import SQLAlchemy or SuperGLM implementation modules.

Acceptance criteria:

- the complete monitoring and SQLite suites pass unchanged;
- persisted canonical JSON and SHA-256 values match v0.2.1 fixtures exactly;
- real frozen-lambda, knot, categorical-identity, offset, and sample-weight
  regressions remain green;
- `pricing_pipeline.modeling.monitoring` remains import-compatible; and
- no implementation module exceeds 700 lines without a documented reason.

## Later consolidation candidates

After slices 1 and 2 are released and used successfully:

1. separate trusted manual-policy replay from editor candidate publication;
2. make the underwriter HTML renderer a clearly generated/static presentation
   component behind the reporting API;
3. isolate scratch benchmarks as explicitly experimental code; and
4. decide from actual ownership and release pressure whether reporting should
   become a separate distribution.

These are not part of the first implementation plan.

## Maintainer documentation

Add `docs/MAINTAINERS.md` as the short, authoritative map. It must answer:

- What is public?
- Where is each command implemented?
- How are notebooks rendered?
- Which module owns each model lifecycle transition?
- Which SQL objects are authoritative?
- Which tests should be run for scaffold, monitoring, publishing, reporting,
  SQL, and a release?
- What must never be logged, committed, or embedded in generated evidence?

It links to detailed notebook and SQL documentation rather than repeating it.
Historical design files are not presented as current operator documentation.
The maintainer page leads with the four-capability map, stays below 200 lines,
and links to detail rather than repeating it.

## Test workflow

Do not delete governance regressions merely to reduce the test count. Document
three test lanes:

- **focused:** the domain being changed, intended for local iteration;
- **integration:** cross-domain notebook, SQLite, publication, and monitoring
  contracts; and
- **release:** full locked suite, Ruff, package build, archive inspection, and
  clean-wheel smoke installation.

The repository records exact commands in `docs/MAINTAINERS.md`. CI may later
run lanes separately, but changing CI is not required for the first slice.

Do not duplicate existing behavioural tests. Slice 1 adds only the minimum
boundary evidence: one parametrized byte-parity test for generated notebooks,
one installed-resource/archive contract, and any single regression required by
an observed extraction failure. Existing scaffold, CLI, packaging, and
clean-wheel tests provide the rest of the evidence.

## Error handling and rollback

Refactoring must preserve sanitized public errors and fail-closed governance
checks. Internal exceptions may become more specific, but public command exit
codes and documented exception types do not change.

Each slice is independently reviewable and revertible. No compatibility facade
is removed in the same release that introduces it. SQL resources are outside
the refactor and therefore require no database rollback.

## Delivery order

1. Capture current scaffold output as a golden contract and write the
   maintainer map.
2. Extract scaffold configuration, resources, rendering, and filesystem
   service behind compatibility exports.
3. Build/install the wheel and prove byte-identical scaffold output.
4. Separately specify and implement the monitoring module split.
5. Only then design the weekly execution command.

This order makes the package easier to understand before adding the weekly
orchestration surface.

## Explicit non-goals

- No feature additions or notebook redesign.
- No YAML/TOML-driven workspace reconciliation.
- No Papermill or weekly runner in this consolidation.
- No SQL migration or schema cleanup.
- No deletion of existing integrity, confidentiality, or concurrency tests.
- No second package or repository split.
- No automatic model publication or deployment.
