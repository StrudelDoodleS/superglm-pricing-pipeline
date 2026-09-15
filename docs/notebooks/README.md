# Notebook workflow and functions

This is the analyst-facing reference. The notebooks contain data and model
decisions; `pricing_pipeline.notebook` handles identifiers, evidence, SQL
writes, artifacts, publication, and deployment guards.

## Workflow boundaries

The standard initial workflow uses 01, 03 and human promotion in 06. Notebook 02
is optional exploration. Notebooks 04 and 05 are optional pricing edits. Notebook
07 is an optional test of the weekly runner; it writes real results when run.
Schedule `monitoring.py` for recurring work. It loads fresh data itself.

| Notebook | Reads | May write | Must not do |
|---|---|---|---|
| `01_data_ingestion.ipynb` | Source data | Verified dataset with provenance | Fit or publish a model |
| `02_model_exploration.ipynb` | Saved dataset from 01 | Selected model configuration as TOML | Publish or deploy |
| `03_model_training.ipynb` | Saved dataset; selected recipe or Python configuration | Manifest, split evidence, run, metrics, candidate, package | Deploy |
| `04_optional_model_editor.ipynb` | Published SQL candidate and bundle | `EDITOR_EDIT` child run/package | Open a draft or deploy |
| `05_optional_manual_adjustment.ipynb` | Deployed or exact published package | Replayable policy plus `MANUAL_EDIT` child; optional explicit deployment | Silently skip missing levels |
| `06_model_deployment.ipynb` | Published SQL package and current champion | Explicit promotion and deployment history | Fit or edit |
| `07_optional_test_weekly_run.ipynb` | SQL champion and fresh source data | Four observations and three saved challengers | Automatically promote |

Notebook 01 saves the prepared dataset. Notebook 02 loads all its rows, applies
your transforms, and fits a local SuperGLM with your feature definitions,
groupings and special levels. It does not require a database connection or a
previously published model.

When ready, export `prototype.toml` from 02 and set
`RECIPE_PATH = "prototype.toml"` in 03. The recipe carries the model choices;
03 reloads the dataset and performs fitting and validation before saving a
version. Its Python configuration remains available with `RECIPE_PATH = None`.
Source queries and accepted enrichment steps belong in 01 so both notebooks
use the same saved data. Exploration source cells are excluded from model-source
identity; the exported recipe is captured when 03 fits the model.

## Underwriter HTML review

After scoring one common review sample, the standalone report runner can compare
frequency, severity, or burn-cost predictions without publishing anything:

```bash
cp docs/notebooks/underwriter_report.example.toml state/underwriter_report.toml
uv run python scripts/build_underwriter_report.py \
  --config state/underwriter_report.toml \
  --allow-local-input
```

The report accepts multiple named prediction columns plus actual and sample-
weight columns. Optional fitted SuperGLM objects supply native main-effect
importance, relativity curves, confidence intervals, EDF, and exposure context;
optional rating workbooks supply exported relativities when an object is not
available. The generated HTML is self-contained, contains aggregate chart data
only, and uses a locally owned stylesheet for its read-only app tabs, context
bar, inspector, metrics, and relativity charts.

When `[superglm_objects]` is enabled, add `--allow-trusted-model-load` and load
only artifacts you trust: Joblib/pickle deserialisation can execute code.

The model-neutral library path needs only scored columns and provides metrics,
weighted prediction KDEs, model movement, Lorenz/gains curves, and double lift:

```python
from pricing_pipeline.reporting import build_scored_model_report

result = build_scored_model_report(
    scored,
    actual="actual",
    predictions={"Current": "pred_current", "Challenger": "pred_new"},
    sample_weight="exposure",
    features=["region", "age"],
    output_path="state/model_review.html",
)
```

Adapters add model-native importance, fitted effects, exact likelihood, and
later interaction evidence without changing the scored-data report core.

Set `problem_type` to `frequency`, `severity`, or `burn_cost`. Frequency and
burn-cost reports expect exposure in `sample_weight`; severity expects claim
count. That setting drives the response, volume, Lorenz/gains and density-axis
labels. Prediction KDEs share one axis and use a scrollable multi-model picker,
so selecting another model never silently changes the comparison scale.

Double-lift selectors choose the numerator and denominator used to rank rows.
Within every weighted bin, actual and predictions are calculated independently
as `sum(weight * value) / sum(weight)`, and the report shows raw exposure plus
exposure share for every bin. A scrollable checkbox picker controls which model
curves are displayed. The rebase selector can then divide all plotted series by
actual or any model in that bin; it changes only the display, never the bins or
underlying aggregates. Prediction distributions are business-weighted Gaussian
KDEs rather than histograms. The same tab has an aggregate model-movement view:
an exposure-weighted rank-migration heatmap shows reranking, while a log-scale
prediction heatmap shows local level changes that similar marginal KDEs can
hide. Cells below `minimum_cell_size` are removed before HTML serialization and
their combined exposure share is disclosed. Lorenz/gains uses the same
multi-model picker and shows equality plus the sample's tie-aware
perfect-ordering curve. Plotly is embedded inside the offline file, so line
charts and heatmaps provide hover, pan, zoom, autoscale, and reset without a CDN.

Double lift also reports quantitative evidence. Common-power row deviance is
decomposed by bin, while bounded line agreement reports clipped weighted Lin
concordance between each displayed model line and actuals: 1 is an exact match
and 0 means no positive agreement. Binned calibration D² remains available as
technical evidence. When both predictions
have training-fitted likelihood metadata, exact held-out NLL is the primary
pairwise score. For compound Tweedie models this is SuperGLM's adaptive full
density calculation: exact Wright--Bessel/series work in its bounded numerical
region and the library's guarded saddlepoint fallback outside it. A supplied
SuperGLM object provides its own fitted `p` and `phi`; otherwise put them under
`[model_likelihoods."Display name"]` in TOML.
The report never estimates either value on review outcomes. With no metadata it
falls back explicitly to deviance. `comparison_unit` can name a policy/cluster
column for the paired interval; its values are used only in memory and never
embedded in HTML. `minimum_cell_size` defaults to 20 distinct comparison units:
double-lift bins are deterministically coarsened until every displayed cell
meets it, and the report refuses samples that cannot satisfy the threshold.
Identifier columns used as `comparison_unit` must not also appear in `features`;
the builder rejects that overlap so identifier levels cannot leak through a
relativity table.

Predictions must already include any model offset and remain on the response
scale. When fitted SuperGLM evidence is collected for a current or holdout
portfolio, pass the exactly row-aligned log offset with `offset=` or configure
the optional `[columns].offset` column. It is used only to verify that the
fitted object produced the supplied predictions: the report does not apply the
offset again or serialize its values. If it is omitted, a retained training
offset is accepted only when the fitted rows and weights are provably aligned.

For SuperGLM-enriched evidence, the compatibility facade keeps the established
signature. Supplied likelihood metadata validates a fitted object's values and
never overrides them:

```python
from pricing_pipeline.reporting import (
    ModelLikelihoodSpec,
    UnderwriterReportOptions,
    build_underwriter_report,
)

report = build_underwriter_report(
    scored_frame,
    actual="actual_response",
    predictions={"Current": "prediction_current", "Challenger": "prediction_new"},
    sample_weight="business_weight",
    features=["feature_a", "feature_b"],
    superglm_models={"Current": fitted_model},
    rating_workbooks={"Challenger": challenger_workbook},
    model_likelihoods={
        "Challenger": ModelLikelihoodSpec(tweedie_power=1.5, dispersion=0.72),
    },
    offset="report_time_offset",  # optional, aligned fitted-evidence binding only
    comparison_unit="policy_id",  # optional; one unit per row when omitted
    output_path="state/underwriter_report/model_review.html",
    options=UnderwriterReportOptions(
        problem_type="burn_cost",
        tweedie_power=1.5,
        movement_bins=10,
        interaction_points=80,
        comparison_bootstrap_replicates=200,
        minimum_cell_size=20,
    ),
)
```

Treat optimiser-selected blend weights as a technical predictive upper bound,
not a pricing recommendation. A production GAM/GBM blend should apply its
governed GAM floor (often 40–50% where that is the business standard) and be
chosen using feature-tail calibration, double lift, sparse-support behaviour,
and repeated-snapshot stability alongside average deviance.

For a full held-out comparison against a local parquet, copy
`scratch_blend_diagnostics.example.toml` to ignored `state/`, fill in the exact
local path and column names, and run:

```bash
uv run python scripts/run_scratch_blend_diagnostics.py \
  --config state/scratch_blend_diagnostics.toml \
  --allow-local-input
```

The 60/20/20 split fits on train, chooses only the technical GAM/GBM weight on
validation, and reserves test for diagnosis. The red comparator is an OOF-
weighted CatBoost/LightGBM/XGBoost blend with fixed, untuned learner settings.
Double-lift bins are balanced by the declared sample weight and ordered by
`boosted blend / GAM`. Pairwise heatmaps first remove both one-way effects from
that log ratio, exposing the interaction the boosted blend added; their second
panel shows held-out boosted-blend-minus-GAM Tweedie deviance. A positive red
cell means the blend is worse there. Always read that beside its support
bar/count: sparse red cells are warnings, not discoveries. The weighted Lorenz
plot reports each model's Gini on the same untouched test rows.

The double-lift presentation follows the CAS RPM model-lift handout: each
curve is indexed to its own portfolio average. The CSV also retains the raw
ratio-of-sums values. Gini is treated only as a ranking statistic, never as a
calibration measure.

The runner fixes one declared Tweedie power in all four models. With aggregate
response `y`, exposure `e`, and credibility weight `w`, trees fit `y / e` with
weight `w * e ** (2 - p)`, which is offset-equivalent Tweedie fitting. Outputs
are aggregate CSV/PNG evidence only under ignored `state/`; no rows, models, or
predictions are retained or published. Every calibration point is a ratio of
sums: `sum(sample_weight * response) / sum(sample_weight)`, with predictions
aggregated using the identical denominator.

## Baseline epochs and monitoring

Notebook 07 and the generated `monitoring.py` run the weekly comparisons.
Notebook 06 reviews and promotes a saved package. The editor is optional when
defining or revising the model:

```text
baseline epoch
  ingest -> fit RAW/ROUTINE_EDIT -> optional editor -> publish -> deploy
                                                          |
                                                   immutable fit contract
                                                          |
monitoring
  ingest a new dated snapshot -> static/frozen/lambda/adaptive comparisons
                              -> SQL evidence and three challenger packages
                              -> review in06 -> explicit promotion
```

The deployed run starts the epoch. Its exact edited model is authoritative, so
the contract includes editor-created groupings, categorical levels and bases,
special levels, monotonic/shape constraints, basis type and dimension, fitted
knots, and fitted REML lambdas. Promoting a saved challenger starts a new comparison epoch. Its exact fitted
state becomes the baseline, with the original declared refit policies preserved.
A change to feature definitions or groupings goes through the model-building
notebooks before publication and promotion.

The [weekly workflow guide](weekly_monitoring.md) shows the generated file,
Windows Task Scheduler and cron setup, SQL review, retries and promotion.
The low-level `run_monitoring_fit` and `persist_monitoring_fit` calls still
produce observations only. `run_monitoring` also publishes the three refits.

For the implementation owners and comparison diagram, see
[From a baseline to monitoring evidence](../package-flows.md#from-a-baseline-to-monitoring-evidence).

The four supported monitoring presets are deliberately limited:

| Variant | Coefficients | REML lambdas | Data-driven knots | Always fixed |
|---|---|---|---|---|
| `STATIC_SCORE` | Deployed | Deployed | Deployed | Groupings, levels, specials, constraints, basis type/dimension |
| `FROZEN_REFIT` | Refit | Deployed | Deployed | Same |
| `REESTIMATE_LAMBDA` | Refit | Refit | Deployed | Same |
| `FULL_ADAPTIVE` | Refit | Refit | Refit | Same |

This gives one clean coefficient-drift view, one smoothing-response view, and
one adaptive challenger. Arbitrary switch combinations are intentionally not
supported because most do not have a stable business interpretation.

## Scaffold configuration

To follow a setting through the implementation, use the
[argument-to-notebook trace](../scaffold-trace.md). It maps CLI flags and TOML
keys to option fields, template tokens and generated notebook cells.

`pricing-pipeline init` seeds `.github/agents/pricing-builder.agent.md` alongside
the config. Select **Pricing builder** in Copilot for help choosing connections,
features, transforms, offsets and validation, and applying those choices to the
notebooks. Init also seeds `.github/agents/pricing-developer.agent.md` for package
maintenance using the framework repository's module index and workflow guides.
Existing config and agent files are preserved when you rerun `init`; missing
agents are added.

At the scaffold root, run `pricing-pipeline init` (or
`python -m pricing_pipeline init` after installation), then edit the generated
`pricing_scaffold.toml`:

```toml
[notebook_defaults]
database_mode = "remote"
runtime_module = "project_runtime.database"
expected_remote_database = "PricingAudit"

[manual_edit_defaults]
source_selector = "deployed"
carry_forward = true
```

```bash
uv run pricing-pipeline scaffold \
  --model-name CLAIM_FREQUENCY \
  --target-name claim_count
```

From a source checkout, `uv run python scripts/scaffold_pricing_model.py` calls
the same installed scaffold command with the same options. It is only an
equivalent checkout wrapper for the final step: the project must already be
initialized and `pricing_scaffold.toml` must exist.

Precedence is command line, explicit `--config`, auto-discovered
`<root>/pricing_scaffold.toml`. There is no built-in-default fallback when the
auto-discovered file is absent; run `pricing-pipeline init`, edit the generated
file, then run `pricing-pipeline scaffold`. Unknown sections or keys fail fast.
`ALLOW_REMOTE_WRITES` cannot be set in TOML.

Each model directory includes `sql/README.md` with an example of loading a
source query from `sql/` in the ingestion notebook. Rerunning the scaffold adds
the folder to existing models and preserves your query files.

`source_selector = "deployed"` makes notebook 05 open the package currently
deployed in the model's configured slot. An exact `PACKAGE_VERSION` in the
notebook overrides it. `carry_forward` is recorded in the canonical policy;
it never causes an implicit publication or deployment.

## Connection guard

Generated notebooks expose four obvious settings:

```python
DATABASE_MODE = "local"  # or "remote"
RUNTIME_MODULE = None  # e.g. "project_runtime.database"
EXPECTED_REMOTE_DATABASE = ""
ALLOW_REMOTE_WRITES = False
```

`connect(...)` creates persistent SQLite databases in local mode. In remote
mode it imports the private runtime module, runs `SELECT DB_NAME()`, rejects a
database-name mismatch, and keeps mutation disabled until
`ALLOW_REMOTE_WRITES = True`.

The private runtime module supplies connectivity without putting secrets in the
repo:

```python
def get_engine(database=None):
    ...

def get_schema_names():
    return {
        "pricing": "python_pricing",
        "pricing_staging": "python_pricing_stg",
        "mlops": "python_mlops",
    }
```

## Dataset and model specification

Notebook 01 records provenance beside the source data and saves the handoff:

```python
from pricing_pipeline.notebook import PricingDataset

dataset = PricingDataset(
    df=df,
    name="my_dataset",
    source="pricing_sql",
    key="row_id",
    as_of="data_as_of",
)
dataset.save(DATASET_PATH, replace=REPLACE_DATASET)
```

`DATASET_PATH` points to `.local/dataset.joblib` under the model directory.
Set `as_of` to the name of the source column containing the dataset's snapshot
date. That column must contain one date with no nulls; no separate date setting
is needed. If the source has no snapshot column, add one using its known reporting
cutoff before creating `PricingDataset`. The saved artifact carries the dataset
name, source, key columns, and date binding, so training does not repeat them.

Notebook 03 loads the dataset and declares transforms once. The generated
mapping starts empty; examples are opt-in:

```python
from superglm import Categorical, Numeric
from pricing_pipeline.models.config import ValidationSplitConfig
from pricing_pipeline.notebook import (
    Clip, Log, Log1p, PricingDataset, PricingModelSpec, apply_transforms,
)

dataset = PricingDataset.load(DATASET_PATH)
df = dataset.df

transforms = {
    # "log_feature": Log("positive_feature"),
    # "log1p_feature": Log1p("nonnegative_feature"),
    # "clipped_feature": Clip("feature_1", lower=0, upper=100),
    # "log_exposure": Log("exposure"),
}
df = apply_transforms(df, transforms)

RAW_FEATURES = {
    "feature_1": Numeric(),
    "segment": Categorical(),
}

MODEL = PricingModelSpec(
    # Model.
    name="MY_MODEL",
    label="My model",
    model_type="superglm_poisson",
    deployment_slot="MY_MODEL_UAT",

    # Data.
    dataset=dataset,

    # Fit and validate.
    target="target",
    features=tuple(RAW_FEATURES),
    validation=ValidationSplitConfig.kfold(n_splits=5, random_state=42, shuffle=True),

    # Save the transforms with the rating tables.
    transforms=transforms,

    # Optional offset, with its coefficient fixed at 1.
    # offset_column="log_exposure",
    # Weights for fitting.
    # sample_weight_column="model_weight",
    # Weights for averaging exported rating tables.
    # export_weight_column="rating_table_weight",
)
```

Pass `RAW_FEATURES` to ordinary `SuperGLM(features=RAW_FEATURES, ...)`. When you
add a transformed feature, use its output name in `RAW_FEATURES`. Each recipe
reads an original source column and creates a new column; chained recipes and
overwriting source columns are unsupported. `Log` computes log(x) and requires
positive values. `Log1p` computes log(1 + x).
`apply_transforms` returns a copy, preserving the saved source dataset.
The model configuration cell starts with `df = dataset.df`, so rerunning it
rebuilds the derived columns from the source snapshot.

Optional offsets use a recipe such as `"log_exposure": Log("exposure")` and
`offset_column="log_exposure"`. The pipeline derives the export details from the
recipe. Sample weight and rating-table export weight remain independent.
The generated model enables none of these optional roles by default.

Notebooks 02 and 03 set `retain_fit_state=False` on their `SuperGLM` constructors.
The freMTPL demo uses the same setting. Prediction, summaries and term standard
errors remain available; the fitted model releases its training caches.
The candidate bundle still carries the data supplied explicitly to the editor.
Set `True` in the constructor if you need `design_summary()` or post-fit shape repair.
When calling reporting or diagnostic functions directly, pass the fitted
weights and offset explicitly rather than relying on retained arrays.

`fit_model` runs cross-validation, refits on all rows, exports the rating
tables and fitted model, and writes the dataset manifest and split evidence.
Its `.metrics` includes held-out `cv_*` scores and full-training `fit_*`
diagnostics, including separate coefficient-solver and REML convergence results.
Inspect its metrics before calling `save_model_version`. Publication saves a
version in the chosen SQL Server database or a `LOCAL_AUDIT` version in local
SQLite. Activation is a separate operation in notebook 06 and requires remote
mode.

New builds preserve supported one-dimensional spline curves by default.
`PricingModelSpec(spline_export="binned", ...)` opts into the previous band
export. Exact export stores a polynomial per knot interval; its displayed
workbook relativity is the value at the interval origin, not a multiplier for
the whole interval. Unsupported exact exports fail instead of becoming bands.
Ordered categoricals remain level lookups. Smooth interactions and LSS models
are outside this publication change.

`pricing.PREDICT_RATE_PACKAGE` evaluates spline segments at the supplied
feature values. The database administrator must apply the current migrations
before publication to SQL Server.
`pricing.V_FINAL_MODEL_RELATIVITY` offers one Power BI view for all effects,
including spline coefficients, input transforms and model/data dates.
Its `representation` column distinguishes lookup values, numeric coefficients,
per-unit factors and splines. Spline rows have NULL `relativity` and
`log_coefficient`; their effects come from `a`, `b`, `c`, and `d`.
For separate datasets, load `pricing.V_MODEL_RELATIVITY` and
`pricing.V_MODEL_SPLINE_SEGMENT` instead. Both layouts use the same stored
effects; exact polynomial coefficients remain in `pricing.PRICING_SPLINE_SEGMENT`.
Power BI can evaluate a common grid across model versions; SQL
scoring uses each policy's actual input. For finite intervals, evaluate
`u=(x-lower_bound)/(upper_bound-lower_bound)` and
`exp(a+u*(b+u*(c+u*d)))`. Unbounded tail segments use `exp(a)` directly.
Respect `upper_inclusive` when matching a finite final endpoint.

Editing a candidate preserves its export choice. Old candidate artifacts use
the binned choice. A clipped spline uses its boundary effect outside the knot
range; a spline configured to reject out-of-range inputs has no tail segments.

Transform recipes are recorded in export metadata and the rating workbook.
The current SQL scorer expects prepared input columns. It does not generate or
run these transforms against raw SQL source data. Prepare the same columns
before scoring and use the recorded recipes to reproduce that preparation.

## Public notebook functions

Import these from `pricing_pipeline.notebook`.

| Function | Use | Main result or guard |
|---|---|---|
| `connect(...)` | Open local SQLite or guarded remote SQL | `NotebookContext` |
| `PricingDataset(df=..., name=..., source=..., key=..., as_of=...)` | Bind source data to provenance | Dataset object |
| `dataset.save(path, replace=False)` | Save notebook 01 output and provenance | Verified Joblib artifact and receipt |
| `PricingDataset.load(path)` | Verify and load the saved dataset | Dataset with `.df` |
| `apply_transforms(df, transforms)` | Apply declared model recipes | Copy with derived columns |
| `save_model_frame(frame, path, replace=False)` | Save a legacy DataFrame handoff | Joblib artifact plus JSON receipt |
| `inspect_model_frame(path)` | Read frame evidence without loading the frame | `ModelFrameArtifact` |
| `load_model_frame(path)` | Verify byte and frame hashes, then load | `pandas.DataFrame` |
| `register_model(pricing, spec, source_root=...)` | Create or validate stable model identity | `RegisteredModel` |
| `fit_model(pricing, model=..., frame=..., superglm_model=..., model_kind=...)` | Run CV, fit the full model and export review artifacts | `BuiltCandidate`; inspect `.metrics` |
| `save_model_version(pricing, candidate)` | Save the fitted version to the selected database | IDs, paths, status, `deduplicated` |
| `load_registered_model(...)` | Resolve one active SQL model by name/label | Review-only `RegisteredModel` |
| `list_model_versions(...)` | List saved model versions newest first | Friendly or technical DataFrame |
| `load_model_version(...)` | Verify and load one saved model version | `Candidate` with bundle and champion snapshot |
| `open_deployed_candidate(...)` | Resolve and open the exact package deployed in the configured slot | `Candidate` carrying baseline run/deployment evidence |
| `publish_edits(...)` | Save and publish an editor session | `EDITOR_EDIT` child publication |
| `ManualAdjustmentPolicy.from_rows(...)` | Define relative level/range multipliers | Canonical replayable policy and SHA-256 |
| `apply_manual_adjustment_policy(...)` | Apply the policy to one clean candidate | `ManualEditReview` with rules, edited model, and portfolio impact |
| `manual_adjustment_policy_from_candidate(...)` | Recover and verify a policy from a published manual child | `ManualAdjustmentPolicy` |
| `publish_manual_adjustment(...)` | Reapply the canonical policy and publish it | `MANUAL_EDIT` child publication |
| `deploy_model_version(...)` | Deploy exactly the reviewed model version | Deployment record; stale champion fails |
| `build_model_fit_contract(...)` | Freeze the deployed model's structural and smoothing evidence | Immutable canonical JSON and SHA-256 |
| `check_monitoring_data(...)` | Check input compatibility and categorical mix changes before the preset loop | Issues, distributions and drift distances; errors can be raised before fitting |
| `load_monitoring_baseline(...)` | Read the current deployment's configuration and fitted state from SQL | `SqlBaseline`; no local model file required |
| `run_monitoring(...)` | Score the SQL champion and publish three refitted challengers from fresh data | `MonitoringReport` with observations, package IDs, metrics and checks |
| `list_challengers(...)` | List published SQL packages and the current champion | DataFrame with monitoring origin and dated model/data identities |
| `review_model_version(...)` | Review an exact package using SQL alone | Immutable selection with `.summary`, `.metrics` and the reviewed champion |
| `run_monitoring_fit(...)` | Score or refit one controlled preset from a SQL baseline or verified deployed `Candidate` | Terms, lambdas, comparable relativities, explicitly weighted metrics, frame/config/result digests |
| `persist_monitoring_fit(...)` | Write a completed observation after lineage checks | Deduplicated monitoring-run receipt |

The previous names remain aliases for existing notebooks:
`build_candidate` is `fit_model`, `publish_candidate` is `save_model_version`,
`list_candidate_versions` is `list_model_versions`, `open_candidate` is
`load_model_version`, and `deploy_package` is `deploy_model_version`.
Arguments and return types are unchanged. New notebook templates use the new
names. Saving a version does not deploy it; local saves remain `LOCAL_AUDIT`.

### SQL baselines and existing notebooks

Updating the package does not regenerate existing notebooks. Completed 01 and 02
notebooks, including feature transforms, groupings, specials and saved recipe
TOMLs, remain usable. Keep their source in version control or make a backup.
Rerun your existing scaffold command without `--force` to add notebook 07 and
`monitoring.py`. Existing notebooks stay intact. See the [weekly workflow](weekly_monitoring.md)
for the small change that gives an existing 06 notebook SQL-only review.

After the database administrator applies migrations through V051, the existing
`save_model_version` call also captures monitoring state in SQL. The snapshot
contains explicit configuration, fitted geometry and smoothing settings, exact
predictions as polynomial/lookup parameters, and aggregate categorical counts.
It does not store training rows or a serialized Python object. Unsupported
snapshot configurations record an unavailable reason; loading one reports it.

Use the same SuperGLM version and Python major/minor version for publication and
monitoring. The loader checks both before reconstructing a model. SQL removes
the dependency on local model files; it does not remove runtime compatibility checks.

For a model published before this update, capture its state once while its
verified model artifact is still available:

```python
from pricing_pipeline.modeling.monitoring import capture_existing_monitoring_baseline

candidate = open_deployed_candidate(pricing, model=model)
capture_existing_monitoring_baseline(candidate)
```

This is an explicit SQL write. It does not fit or deploy a model. Subsequent
monitoring loads use SQL only. If the old model file is already gone, its recipe
alone cannot recover the old coefficients and learned knots. Publish a complete
reviewed model to establish a new baseline.

The generated weekly workflow calls `run_monitoring` to fit and publish the
challengers. For custom observation-only workflows, the lower-level calls below
load the baseline once and run individual comparisons:

```python
from pricing_pipeline.notebook import (
    MonitoringVariant, check_monitoring_data, load_monitoring_baseline, run_monitoring_fit,
)

baseline = load_monitoring_baseline(pricing, model=model)
check = check_monitoring_data(baseline, X_new, sample_weight=weight_new)
display(check.issues, check.drift)
check.raise_for_errors()  # Warnings allow fitting; incompatible inputs stop here.

results = {
    variant: run_monitoring_fit(
        baseline,
        X_new,
        y_new,
        variant=variant,
        sample_weight=weight_new,
        offset=offset_new,
        model_frame=frame_new,
        target_column=model.spec.target,
        offset_column=model.spec.offset_column,
    )
    for variant in MonitoringVariant
}
```

The check compares against reference counts and weights saved in SQL. New raw
categorical levels, missing feature columns, nulls, invalid numeric values and
invalid weights block controlled refits. Known levels with no rows or no positive
weight produce a support warning. Grouped features are checked against their
original input levels, and ordered categories include their specials.

Refits also require support to estimate each feature:

- Numeric features need at least two distinct values with positive fitting weight.
- Ordered splines need positive-weight observations for every declared smooth
  group or level. Losing one member of a surviving group only warns. Losing the
  entire group blocks the refit, including `FULL_ADAPTIVE`. Specials do not count
  as observations of the smooth; absent specials retain the support warning.
- Continuous splines need observations inside the saved domain and variation
  after applying their extrapolation policy. A shift from `0–100` to `200–300`
  blocks a controlled refit. A smaller range such as `50–100` warns about lost
  tails and empty saved knot intervals.
- Out-of-bound rows raise with `extrapolation="error"` and warn with `"clip"` or
  `"extend"`. Adaptive fits may move data-driven boundaries, but retain explicit
  boundaries and knots. Declared knots outside the new adaptive domain block.

The check defaults to `variant="FROZEN_REFIT"`. Pass the variant when checking a
specific comparison. `variant="STATIC_SCORE"` checks prediction compatibility
without requiring support for re-estimation. Every `run_monitoring_fit` call
enforces the checks for its own variant before REML starts.

These checks use positive weight, not row presence, to assess fitting support.
Out-of-bound errors include zero-weight rows because the model still evaluates
their feature values. Coverage warnings do not certify a reliable fit: these
checks do not test joint rank, near-collinearity, or numerical conditioning.
Inspect fit diagnostics as well. No check moves knots, changes groupings, chooses
a refit strategy, or establishes a new baseline automatically.

`check.distributions` contains per-level counts and shares for both snapshots.
`check.drift` measures categorical total variation distance: half the sum of
absolute share changes, between zero and one. It reports row shares and, when
weights exist on both sides, fit-weight shares. It does not compare exposure shares
unless those weights represent exposure. `drift_threshold=0.2` is a configurable
review trigger, not a significance test or an automatic decision to rebase.

For a standalone fitted SuperGLM, supply `reference_df` and optional
`reference_sample_weight`. Missing reference data explicitly leaves drift
unassessed. Numeric distribution drift, changed label meanings with unchanged
marginals, and the cause of a detected change are outside this categorical check.
Continue using dashboard trends and upstream investigation for those questions.

`check.to_json()` returns aggregate evidence for a runner's logs or an artifact.
This preflight report is not automatically persisted to SQL or a dashboard.
`run_monitoring_fit` also enforces compatibility before fitting, so bypassing the
explicit check cannot silently accept new levels or unsupported refits. Direct `STATIC_SCORE` calls
retain an existing ungrouped categorical `unseen="base"` prediction policy;
that fallback does not permit refitting unknown levels.

Persist only after all requested fits have succeeded. Pass the new snapshot's
`manifest_id`, `baseline.model_run_id`, and
`baseline.deployment_id`. Exact retries deduplicate; a
different data-as-at/manifest creates a new observation.

For persisted evidence, use a baseline returned by `load_monitoring_baseline`.
Loading verifies its JSON digest and SQL source lineage. Persistence checks the
baseline state and current deployment again, so a deployment change during the
fits prevents saving observations against a stale champion. The existing
`Candidate` path remains available and verifies its local model artifact. A raw
fitted `SuperGLM` is supported for local simulation; its result cannot be persisted. The
ordered `model_frame` must hash to the supplied observation manifest at
persistence time. If the deployed fit contract declares a sample-weight or
offset input, the new snapshot must supply it; an offset is rejected when the
deployed model was fitted without one.

The post-fit guard verifies the fitted object, not just its input config. For
protected quantities it requires exact equality: structure and governed
level/grouping metadata, knot and boundary arrays, final lambdas, fixed-lambda
policy, and every fixed-lambda REML history step. `FROZEN_REFIT` also requires
SuperGLM's `fixed_lambdas` termination reason. A mismatch raises before a
result can be persisted. SQL stores the canonical evidence JSON and its SHA-256
with `invariant_status = 'VERIFIED'`, plus the exact ordered-frame, fit-config,
and complete-result digests. Metric names state their weighting explicitly,
for example `sample_weighted_mean_prediction`.

To reproduce a synthetic 60% baseline followed by four 10% arrivals, including
out-of-time scoring and drift figures:

```bash
uv run python scripts/simulate_model_monitoring.py
```

Outputs go to ignored local state under `state/monitoring_simulation/`.

`register_model`, `fit_model`, `save_model_version`, `publish_edits`,
`publish_manual_adjustment`, and `deploy_model_version` call the context write guard.
Editor/manual publication and deployment require remote mode.

## Manual business adjustments

Notebook 05 shows every published package with model kind, fit time,
data-as-at, parent and deployment state. It opens the current deployment by
default. Each policy rule names a feature, either exact levels or a numeric
range, a positive multiplier, and a reason. Python converts the multiplier to
the model's log-link shift; missing levels, overlapping rules, invalid factors,
and invalid preview predictions fail before publication.

The resulting package is an immutable `MANUAL_EDIT` child. Its SQL revision
metadata contains the canonical policy payload and digest as well as the
normal editor artifact evidence. Publication and deployment are separate
cells. The optional deployment cell defaults to off.

`carry_forward = true` means that the relative policy is intended to be
replayed against a later clean candidate. Apply it to that new base model, not
to the previous `MANUAL_EDIT`, so an uplift does not compound. Weekly refits do not automatically replay this policy. Applying an adjustment
to a later fit remains a separate reviewed publication step. Monitoring
observations retain their unadjusted comparison metrics.
Set `POLICY_SOURCE_PACKAGE_VERSION` to an earlier `MANUAL_EDIT` package to load
and verify its policy from SQL rather than typing its rules again. Replay is
refused when that policy recorded `carry_forward = false`; the trusted publisher
also reloads the parent and replays the canonical policy before accepting the
submitted model.

## Validation splitters

`PricingModelSpec.validation` accepts a splitter with `.split(df, y, groups=None)`
as well as `ValidationSplitConfig`. Set this before calling `register_model`.

For grouped validation:

```python
from dataclasses import replace
from sklearn.model_selection import GroupKFold

MODEL = replace(
    MODEL,
    validation=GroupKFold(n_splits=5),
    groups_column="customer_id",
)
```

`fit_model` passes the named column as `groups`. It must exist and contain no
null values. The group column does not have to be a model feature.

For walk-forward validation:

```python
from sklearn.model_selection import TimeSeriesSplit

MODEL = replace(
    MODEL,
    validation=TimeSeriesSplit(n_splits=4, test_size=1_000, gap=100),
    groups_column=None,
)
```

Prepare and save the dataset in chronological order first. `fit_model` does not
sort it. `TimeSeriesSplit` measures `gap`, `test_size` and `max_train_size` in
rows. Use a custom splitter for calendar windows or to keep all records from
one date together.

Custom splitters receive a copy of the full prepared dataframe, the target
series, and the group series when `groups_column` is set. This includes date
and business columns outside the model features. Yield pairs of integer row
positions, not dataframe index labels. Each fold needs nonempty, disjoint
training and test sets. A row may be tested only once across all folds;
overlapping test windows and repeated CV are rejected. Training rows may recur
across folds. Partial test coverage is allowed and reported as `cv_oof_coverage`.

The splitter runs once per build. Fitting replays those exact folds and
publication saves them in the split artifact. SQL records the splitter class,
settings and group-column name. Settings come from `get_params()` when present,
otherwise from attributes matching constructor arguments. Settings must be
JSON-compatible; NumPy scalars and arrays are supported. Use integer random
seeds rather than `RandomState` or generator objects.

Use `ValidationSplitConfig.column_kfold(column="cv_fold")` when the dataset
already contains fold assignments, or `column_holdout(...)` for explicit
training/test labels. These remain available alongside splitter objects.

## Data-as-at and manifest identity

`data_as_of` is the date through which source data is complete. Keep a constant,
non-null date column in the saved dataset and declare it with
`PricingDataset(..., as_of="data_as_of")`. Legacy specs may still set
`data_as_of_column`. An explicit `data_as_of=` may be used instead; if both
exist, they must match.

The manifest records the date and column name, dataset/source names, primary
keys, column roles, row count, ordered-frame SHA-256, dtypes, statistics, and
runtime hash metadata. Changing data or data-as-at creates a new manifest.
Changing validation configuration or exact split indices creates a new split
set under the same manifest.

## Existing routine grouping artifacts

New models can define groupings directly in 02 and carry them to 03 in the
recipe. Earlier projects may instead use the separate artifact workflow below.
Notebook 03 still supports those artifacts when `RECIPE_PATH = None`.

Until SuperGLM provides a public grouping export API, the workbench owns one
isolated compatibility bridge to its private grouping object:

1. Publish the untouched `RAW` candidate in notebook 03.
2. Open that published RAW candidate with `load_model_version(...)`.
3. Use `EditorSession` to collapse any levels across any categorical features.
4. Call `export_level_groupings(candidate, editor_session=..., path=...)`.
5. Notebook 03 calls `load_level_groupings(...)` and
   `apply_level_groupings(...)`, then fits `ROUTINE_EDIT`.

The ignored Joblib artifact stores the actual `dict[str, LevelGrouping]` Python
objects. Its JSON sidecar is readable integrity/provenance evidence, not a
hand-edited grouping config. Loading checks SuperGLM/Python versions, model,
source package, manifest, frame hash, data-as-at, feature names, levels, and the
group partition. Missing or no-op groupings skip the routine-edit build.
Grouping artifacts are deliberately tied to the exact SuperGLM version; after
an upgrade, reopen the RAW candidate and export them again.

Grouping is Python model behaviour. SQL receives completed relativities and
evidence; it does not execute grouping rules.

## Publication and duplicate handling

Immediately before SQL staging, Python fingerprints final rating semantics:
base rate, terms, levels, group mappings, metadata, and relativities. Legacy
numbers are canonicalized to 10 decimal places and row order is ignored.
Spline coefficients and their bounds retain full stored precision in the
fingerprint, so a coefficient-only change creates a different model identity.

The lookup key is:

```text
model_id + manifest_id + model_kind + model_equivalence_sha256
+ recipe_status + recipe_sha256 + validation split identity
```

An equivalent successful build reuses the existing run/package and returns
`deduplicated=True`; it does not create staging rows. A different manifest or
model kind remains distinct. Different recipes or fold assignments retain separate
build evidence. Unsupported recipes retain exact-export retries and skip cross-export
equivalence because their declared identity is unavailable. A different requested effective date raises
instead of silently discarding release intent.

## Artifact locations

Generated notebooks keep ignored local handoffs below the model directory.
New build folders use compact run keys and short digest components to remain
usable in Windows Explorer. Full identities remain inside receipts, bundles,
and SQL.

## Export and reload model recipes

Keep Python authoring for the first build. The training notebook's explicit
`RECIPE_PATH = None` selects that branch; a path selects recipe loading. A file's
existence never changes the selected model. Export a selected completed build:

```python
raw_candidate.recipe.save(MODEL_DIR / "raw_model.toml")
# If a routine fit applied groupings, export that candidate separately.
routine_candidate.recipe.save(MODEL_DIR / "routine_model.toml")
```

A prototype can be exported before framework training. Supply its flat spec so
that target, transforms, offset, weights and validation are explicit:

```python
from pricing_pipeline.notebook import ModelRecipe

ModelRecipe.from_model(prototype, spec=MODEL).save(MODEL_DIR / "model.toml")
recipe = ModelRecipe.load(MODEL_DIR / "challenger.toml")
MODEL, glm = recipe.build(dataset=dataset)
df = apply_transforms(dataset.df, MODEL.transforms)
model = register_model(pricing, MODEL, source_root=MODEL_DIR)
candidate = fit_model(pricing, model=model, frame=df, superglm_model=glm)
saved = save_model_version(pricing, candidate)
```

`load` and `build` reconstruct an unfitted model without SQL access. `save` writes
only TOML and requires `replace=True` to replace a file. Constructor defaults are
explicit; `{ none = true }` records an unset option because TOML has no null.
Feature and transform table order determines construction order. Add a challenger
with one new `[features.name]` table. Transform-derived offset source/label fields
are omitted: changing the transform source updates that offset contract on load.
Explicit offset contracts without a transform remain in the file. Older documents
with explicit order arrays still load; remove those arrays to use table order.
Group entries retain every member, including singleton
groups; typed domains and ordered numeric positions remain separate from grouping
labels. Specials remain free levels outside the ordered smooth. When a special
uses a different typed domain label, `special_domain` preserves that reporting
label alongside its raw matching declaration.

The actual configuration is captured at the validated fit boundary, before CV or
full fitting. Python overrides affect that snapshot; later changes to Python
objects or TOML cannot change a completed build's recipe. The saved result exposes
`recipe_revision`, `recipe_sha256` and `recipe_status`. SQL assigns revisions in
the publication transaction. Same recipe with new data keeps its revision; a
previous recipe reused later keeps its original revision. Weekly monitoring
refits inherit the champion's declared recipe too. Use `pricing.V_MODEL_REGISTRY`
to see that `definition_revision` beside the model's champion/challenger role.
Package and run IDs identify saved fits; `fit_version` is the legacy fit counter.
Saving never deploys.

Recipe mode skips `.local/routine_groupings.joblib`. Apply any further grouping
explicitly in Python and fit again. Post-fit editor/manual packages inherit the
training recipe and retain their separate edit/parent evidence. A training recipe
alone does not reproduce those coefficient edits. Ordinary recipe loading refits
declared choices; frozen learned knots, bases, lambdas or coefficients still use
the SQL baseline and monitoring variants.

Supported recipes include Numeric, Polynomial, Categorical, OrderedCategorical,
one-dimensional spline variants and the existing categorical interactions, plus
Log, Log1p and Clip transforms. ValidationSplitConfig, sklearn KFold, GroupKFold
and TimeSeriesSplit have explicit codecs. Other Python objects can still fit
through the existing API with `UNSUPPORTED` recipe status and a reason; they
cannot be exported or claim a recipe revision. Historical artifacts remain
`LEGACY`. No new interaction or LSS export support is added.

The database administrator must apply SQL migrations V047 and V048 before
models are saved with this version. Local SQLite
stores upgrade on opening. The [comparison notebook](../../tutorials/model_recipes/comparison.ipynb)
exercises grouped/special-level parity and a saved challenger. `init` continues to
preserve existing customized builder agents; update those files intentionally
from the packaged `pricing-builder.agent.md` when adopting this workflow.
