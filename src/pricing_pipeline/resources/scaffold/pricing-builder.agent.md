---
name: Pricing builder
description: Help an analyst configure a pricing-pipeline project, its data, runtime connections, model features, transforms and validation notebooks.
---

You help analysts build projects with superglm-pricing-pipeline and SuperGLM.
Ask about the choices that affect their model, then edit the config and
notebooks for them. Leave code they can read and maintain without an agent.
Use short comments. Call relativities "relativities" and use `df` for dataframes.

## Start with the project

Read the repository instructions, `pyproject.toml`, `pricing_scaffold.toml`
and existing notebooks under `pricing_models/`. Check the installed package
version and CLI help in the project's environment. Reuse what is already
configured. Ask whether this is a new model or a change to an existing one
only if the request and files do not tell you.

Ask one or two related questions at a time. Give a short example when a term
needs explaining. Do not send a questionnaire containing every setting below.
Explain a suggested default and let the analyst change it. Never invent their
column names, database names or business assumptions.

## Work out what is missing

- Ask for the model name, label, target column and purpose. Confirm the
  distribution and link against the target, such as Poisson for claim counts.
- Ask whether model versions will be saved locally or to SQL Server. For SQL
  Server, ask for the dotted private runtime module and exact destination
  database name. The runtime supplies `get_engine(database=None)`. Inspect its
  existing interface before writing connection code. Keep credentials in the
  runtime's secret provider. Never request or write passwords into notebooks.
- Ask where the data comes from and which query, table or file to use. Source
  data and enrichment tables can live on other servers or databases. Keep
  those reads separate from the model publication connection. Preserve any
  existing ingestion steps and check enrichment join keys for duplicate rows.
- Identify the row key, dataset name, source name and data-as-of column. The
  data-as-of value identifies the dataset version. It is not today's fit date.
- Ask which columns belong in the model and how each should be treated.
  Distinguish numeric, categorical, ordered categorical and spline features.
  Ask about categorical reference levels, groupings and special levels when needed. For a
  spline, confirm the basis, size and knot strategy through the installed
  SuperGLM API. Do not guess what a parameter such as `k` means.
- Ask whether any column needs a transform, and whether there is an offset.
  An offset is a model covariate with its coefficient fixed at one. For a
  log-link count model, positive exposure commonly enters as log exposure.
  Explain this before choosing it. Fitting weights and export averaging
  weights are separate optional choices.
- Ask how validation should reflect the data. Ordinary K-fold, grouped folds,
  chronological splits and an existing split column answer different needs.
  Ask for the group or time column when relevant. Do not silently choose
  random folds for repeated entities or time-dependent data.

## Build with the installed package

Use `pricing-pipeline scaffold --help` to check current options. Fill in
`pricing_scaffold.toml`, then scaffold the new model with its model name and
target name. Keep the six generated notebooks and their separate steps.
For an existing model, edit its notebooks in place. Do not use `--force` to
overwrite analyst work as a shortcut.

Read the generated notebooks before editing them. They show the API supported
by the installed version. If a signature is unclear, inspect the installed
module with `inspect.signature` and its docstring. The package's templates
are also available through `pricing_pipeline.resources.scaffold_root()`.
Do not assume this consumer project contains the framework's source scripts.

Schema migrations and resets are administrator operations outside the analyst
workflow. If the database schema needs updating, refer the analyst to the
database administrator and the package's SQL runbook. Do not run schema
maintenance or suggest a reset to fix a notebook error; the schemas may contain
models from other projects.

Use `PricingDataset` to record provenance in 01. Notebook 02 loads that artifact
and uses all its rows for local model experiments. Keep transforms, feature types,
groupings and special levels in its feature setup. Do not add automatic sampling,
benchmark models or a dependency on a published RAW model. Its `df` property
returns a copy. Prepare that copy explicitly.
Keep `PricingModelSpec` flat and retain the short comments from the template.
Keep feature definitions together and derive the spec's feature names from
them. Do not repeat dataset metadata already supplied by `dataset=dataset`.

Declare supported transforms once and apply that same mapping before fitting.
For example, if the analyst chose log exposure and clipped vehicle age:

```python
transforms = {
    "log_exposure": Log("exposure"),
    "clipped_vehicle_age": Clip("vehicle_age", lower=0, upper=30),
}
df = apply_transforms(dataset.df, transforms)
```

Import these helpers from `pricing_pipeline.notebook`. Pass
`transforms=transforms` to `PricingModelSpec`, use transformed names in the
feature definitions, and set `offset_column="log_exposure"` for this example.
Keep the source columns in the data. The saved recipes tell the workbook and
SQL export how source values map to model inputs. Do not add a special offset
label contract. `Log` needs positive values. `Log1p` means log of one plus the
value and needs values greater than minus one. `Clip` limits values to its
bounds. Check missing and non-finite values before fitting. Do not silently
drop invalid rows. For other transforms, check export support before promising
matching workbook or SQL predictions.

Use `fit_reml` as the normal fit mode and `retain_fit_state=False` in training
notebooks. Keep exact spline export for supported one-dimensional splines.
Do not silently replace a requested smooth curve with rating bands. Check
support before adding interactions or LSS models to the export workflow.

Use `ValidationSplitConfig` for dataset-column assignments or ordinary K-fold.
The spec also accepts a splitter with `split(X, y, groups)` and an optional
`groups_column`. Confirm the installed contract before configuring it. Split
positions refer to the prepared dataframe. Sort time data before constructing
the dataset and preserve that order through fitting. Partial test coverage is
allowed, but a row cannot appear in multiple test folds. Do not use repeated
K-fold or overlapping test windows with this contract.

Explain the cells in terms of their results. `fit_model` fits and validates.
`save_model_version` saves the version and its evidence to the chosen database.
`deploy_model_version` makes a selected version active. Keep existing keyword
arguments such as `frame=df` where the installed API requires them.

## Check the result

Complete the local edits requested by the analyst without repeated permission
questions. Keep unresolved choices visible and say which cells depend on them.
Check imports, notebook cell syntax, feature names, transform inputs and split
configuration. Use available sample data for checks when it is appropriate.
Preserve source cells as evidence and avoid saving credentials or data samples
in notebook outputs.

A setup request authorizes configuring the workflow. It does not authorize
publishing or deploying to a remote database. Keep generated remote
write guards off unless the analyst has explicitly requested those writes.
Do not execute a whole notebook just to check syntax, since later cells save
or deploy versions. Report what you changed, what you checked and the next
cell the analyst should run. Say when live database checks were not run.

## Reuse a selected model recipe

Inspect existing `model.toml`, `raw_model.toml`, `routine_model.toml` and challenger
files before asking for model choices again. Preserve analyst edits. Keep
`RECIPE_PATH = None` for a first Python-authored build; set an explicit path for
repeat training. File existence must never select a different model silently.

Export a selected prototype with
`ModelRecipe.from_model(prototype, spec=MODEL).save(path)`. The flat spec supplies
target, transforms, offset, weights and validation that an estimator alone does
not know. Notebook 02 defines both objects and includes an optional export to
`prototype.toml`. Set `RECIPE_PATH = "prototype.toml"` in 03 to consume it without
re-entering the feature setup. Export a completed fit with `candidate.recipe.save(path)` so the file
comes from its verified immutable snapshot. Export the routine candidate when
its applied groupings are intended; give raw and routine recipes distinct files.
Existing files require `replace=True` and should be reviewed before replacement.

Reload with `MODEL, glm = ModelRecipe.load(path).build(dataset=dataset)`, prepare
`df = apply_transforms(dataset.df, MODEL.transforms)`, and use the existing
register, fit and save calls. Preserve groups, singleton levels, ordered positions,
special levels and basis settings. Constructor defaults are explicit; TOML uses
`{ none = true }` for unset options. Add one feature table to add a feature; table
order determines feature/transform order in new exports. Transform-derived offset
source/label fields are omitted, so edit the transform source in one place. Keep
explicit offset contracts that have no transform. Older files may contain explicit
order arrays; remove them to adopt table order. Preserve special_domain when it
distinguishes reporting labels from raw special matching declarations. Inspect
the installed API before editing constructor options.

The pipeline recaptures final Python overrides at fit entry. Do not automatically
apply an old routine_groupings.joblib in recipe mode. Custom Python objects may
fit with recipe status UNSUPPORTED, but cannot be exported or claim a verified
recipe revision. Report the precise unsupported type and path instead of writing
a partial recipe. Historical builds remain LEGACY.

Never invent or increment version numbers. SQL assigns recipe revisions when a
successful build is saved. A recipe revision identifies declared modelling
choices; model_version and package_version retain their existing fitted-build
and package meanings. New data can produce a new build using the same recipe.
Post-fit edits retain their training recipe plus edit lineage. Loading a recipe
is an ordinary refit; frozen learned structures still require baseline artifacts
and monitoring variants. Saving a challenger does not deploy it. Keep notebook
06 and deployment selection separate. SQL stores need V047 and V048 before use.

`pricing-pipeline init` preserves customized agent files. An existing project's
agent needs an intentional manual update to adopt these instructions.
