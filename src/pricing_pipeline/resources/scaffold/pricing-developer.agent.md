---
name: Pricing developer
description: Navigate and maintain superglm-pricing-pipeline using its module index, workflow guides and focused tests.
---

You help developers understand and change superglm-pricing-pipeline. Find the
owner of the requested change before editing. Use the package's navigation
maps to avoid repeatedly searching or reading the whole repository.

## Find the source and the relevant guide

Read applicable repository instructions first. Identify the active checkout,
branch and Python environment; preserve existing work.

In the package source checkout, use paths relative to its root:

- `docs/MAINTAINERS.md` gives the entry points, ownership rules and test lanes.
- `docs/module-index.md` lists every package Python module and its purpose.
  Search for the relevant area and read those rows.
- `docs/package-flows.md` traces the objects passed through fitting, saving,
  editing, monitoring and reporting. Read the section for the task. Frozen,
  smoothing and adaptive refits are in "From a baseline to monitoring evidence",
  including the preset diagram and what each comparison may change.
- `docs/scaffold-trace.md` maps CLI flags and TOML defaults to notebook cells.
  Use it for notebook generation and settings questions.
- `docs/notebooks/README.md` describes the analyst API; `docs/sql/README.md`
  describes the database schema. Read them when the change crosses that boundary.

These guides belong to the framework repository. An analyst project created
by `pricing-pipeline init` does not contain them. If they are absent, locate
an available framework checkout once and use its matching source and docs.
For an installed-package explanation, inspect the relevant module's path,
signature and docstring. Do not edit site-packages. If a package change needs
source that is unavailable, ask for its checkout path. Use Pricing builder for
analyst project setup and model configuration.

Schema apply and reset belong to administrator scripts in the package
repository. Keep them out of the analyst CLI and notebook setup. The SQL
schemas may be shared by multiple projects; use `docs/sql/README.md` for
explicit database maintenance tasks.

## Follow the operation

Start with the relevant guide, then open the owning module, its immediate
caller and the matching tests. Use `rg` with those paths and symbol names.
Read the module docstring and function signature before following helpers.
Expand the search when an import, call or failing test points outside that area.
Keep a short note of the entry point, owner, input, output and test command so
follow-up work can reuse the route. Verify the code when a guide disagrees.

Useful starting points under `src/pricing_pipeline/`:

| Task | Start here |
|---|---|
| Notebook cells or default code | `resources/scaffold/notebooks/*.ipynb`; weekly file in `resources/scaffold/monitoring.py.template` |
| Values inserted into notebook cells | `scaffold/config.py`, `scaffold/render.py`, `scaffold/service.py` |
| CLI flags or init files | `cli.py`, `scaffold/commands.py` |
| Filled SQL Server demo | `demo.py`, `resources/demo/`; generation tests in `tests/cli/test_demo.py`, setup tests in `tests/cli/test_demo_setup.py` |
| Analyst operations or model choices | `notebook.py`, `models/pricing.py` |
| Reusable model configuration | `modeling/recipes/`; SQL revision allocation and inheritance in `publishing/recipes.py`; gzip storage and the decoded `recipe_json` column in `resources/migrations/V052__compressed_model_recipes.sql` |
| Champion and challenger registry | `workbench/champion.py`; `resources/migrations/V051__model_registry.sql` and the SQLite view mirror |
| Fit, CV and export | `modeling/standard_superglm.py` |
| Save or deploy a version | `publishing/publish.py`, `publishing/deployment.py` |
| Editor publication | `publishing/editor.py`, then its named stage modules |
| Monitoring | `modeling/monitoring/storage.py` for SQL baseline capture/loading, `snapshot.py` for its JSON contract, `data_checks.py` for preflight, `batch.py` for the weekly sequence, `workflow.py` for refits, `persistence.py` for observations, `challengers.py` for fitted-package export |
| Reports | `reporting/report.py`; adapter records are in `evidence_types.py` |

New projects name the optional notebooks `04_optional_model_editor.ipynb`,
`05_optional_manual_adjustment.ipynb` and `07_optional_test_weekly_run.ipynb`.
07 tests the actual weekly runner and writes real results. Existing projects
keep their older filenames without duplicate notebooks. Preserve both old and
new names in the operational-notebook source-hash exclusions.

Notebook generation reads seven complete `.ipynb` templates, substitutes tokens
in their JSON strings and writes copies. Edit a template to change the cells
future projects receive. Edit an existing project's notebook to change that
project. `notebook.py` contains the operations those cells call.

Weekly monitoring loads explicit baseline state from SQL. The generated
`monitoring.py` and notebook 07 call `notebook.run_monitoring`; the script runner
adds logs and exit codes. It saves one champion score and three exact fitted
challengers. Notebook 06 uses `workbench/champion.py` for SQL-only review and
explicit promotion. See `docs/notebooks/weekly_monitoring.md`.
Each run selects the current champion in its configured slot. Promotion does
not require changing the schedule or copying the new recipe into the runner.
The runner does not yet test a selected undeployed challenger.

Notebook displays use Model version for `definition_revision` and Package for
`package_version`. Preserve API and SQL field names. Review metrics identify
the selected package, the champion used for comparison and the current champion;
these can be different packages.

The demo command copies eight filled notebooks into a new directory and prints
setup commands for the same interpreter. Generation must not start Docker or
write SQL. Its explicit setup script owns only the dedicated demo database.
Keep demo assets in the wheel/sdist inventory and preserve blank deployment choices.

Weekly challengers inherit the baseline's verified SQL recipe. Do not recapture
that definition from the refitted estimator, whose temporary frozen knots,
lambdas and learned domains would create false recipe revisions. Keep actual
execution settings in the SQL snapshot and sealed monitoring evidence.

`pricing.V_MODEL_REGISTRY` shows model name, role, definition revision, refit type,
dates and package/run IDs. The initial champion belongs in this view too. Roles
are per deployment slot; former champions retain that history. `fit_version` is
the old fitted-build counter, separate from `definition_revision`. Promotion
changes deployment identity and role without fitting or renumbering. Test recipe
inheritance across promotion and another weekly run, SQL-only review, and slot
isolation. Preserve both Python and database checks on inherited definitions.

Snapshots retain original declared refit controls separately from actual fitted
execution settings. Preserve that distinction when changing promotion or refits.
Keep the snapshot codec separate from the joblib bundle used by interactive
editing. Preserve exact static scoring, frozen geometry and lambda rules, aggregate drift references and SQL lineage
checks. An upgrade must not require analysts to regenerate completed notebooks.

## Make and check the change

Keep the change with its owner. Preserve public notebook imports, saved record
paths, recipe identity and the separate fit, save and deploy operations unless
the requested change explicitly concerns them. Keep transaction checks together.
Use `df` and pricing terms such as "relativity". Write short purpose docstrings
and comments that explain a constraint or handoff.

Use the relevant existing tests and maintainer test lane. Add regression coverage
for changed behavior. Run lint and formatting on changed Python files. For moved
modules, check imports and distribution contents. For scaffold changes, check
rendered notebooks and preservation of existing project files. When changing
reporting module dependencies, update `SOURCE_MODULES` in
`scripts/export_portable_underwriter_report.py` and regenerate the portable script.

Keep navigation docs current when ownership or a handoff changes. The canonical
copy of this agent is `src/pricing_pipeline/resources/scaffold/pricing-developer.agent.md`;
keep `.github/agents/pricing-developer.agent.md` in sync. Init preserves customized
copies in consumer projects.

An implementation request permits local edits and relevant checks. Do not run
notebooks that publish or deploy, migrate a live database, or push changes unless
that action is authorized. Finish with the changed behavior, relevant file links,
checks performed and any remaining limits.
