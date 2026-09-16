# Run weekly challengers and promote a champion

Schedule `pricing_models/<model>/monitoring.py` using the Python interpreter from
your project environment. `07_optional_test_weekly_run.ipynb` is an optional way
to test the same `run()` function during setup or debugging. Scheduled monitoring
does not require the notebook. Its test run writes real observations and packages.

The script loads fresh data, reads the deployed baseline from SQL, checks input
compatibility, scores the champion and fits three challengers. It saves the
observations and each challenger's exact fitted rating package to SQL. The current
deployment stays in place until you explicitly promote a package in notebook 06.

| Variant | What is re-estimated |
|---|---|
| `STATIC_SCORE` | Nothing; score the saved baseline |
| `FROZEN_REFIT` | Coefficients |
| `REESTIMATE_LAMBDA` | Coefficients and smoothing lambdas |
| `FULL_ADAPTIVE` | Coefficients, smoothing lambdas and data-driven knots/boundaries |

Explicit knots and boundaries remain fixed. All four preserve the feature
definitions, groupings and special levels of the baseline.

## Model versions and package numbers

Use these two numbers when reviewing a model:

| Notebook label | What it identifies | SQL/API field |
|---|---|---|
| Model version | Declared model configuration, including features, groupings, special levels and fit settings. Weekly refits retain it. | `recipe_revision`, also exposed as `definition_revision` |
| Package | One saved rating result to inspect or promote. Multiple packages can share a definition. | `package_version` |

For example, model version 1 can have package 1 as champion and packages 2, 3 and 4
as weekly challengers. Promoting package 4 makes it champion, still under
model version 1. Saving a changed feature set creates a new model version, or
reuses the number of an identical definition saved earlier. Exact publication retries
can reuse an existing package. Both numbers belong to the registered model;
include its name when comparing different models.

`Role` is the deployment status, not another version. `Current champion package`,
`Compared with package` and `Parent package` refer to packages from that same
numbering system. The comparison package can be a former champion by review time.

The older `model_version`, exposed as `fit_version` in registry and monitoring
results, is an internal fit counter such as `v5`. It can have gaps after failed
attempts and does not identify a model definition. The notebook tables omit it.
It remains available in the full API results and SQL for existing consumers.

Other versions describe different things: a manual adjustment's policy version,
the recipe or snapshot format, database migrations, and installed Python libraries.
They do not select a champion. The optional adjustment notebook labels its policy
version explicitly; the normal review tables show Model version and Package.

## Configure once

After installing the package update, rerun your original `pricing-pipeline
scaffold` command without `--force`. It adds missing notebooks and monitoring.py and preserves
your existing files, including completed 01, 02 and 03 notebooks. Existing 04, 05 and 07
notebooks keep their previous filenames; the scaffold does not add duplicate copies. For example:

```bash
uv run pricing-pipeline scaffold --model-name BURN_COST --target-name burn_cost --package-name burn_cost
```

Keep your model name, package name and deployment slot consistent with the
existing project. The database needs migrations through V052, and the deployed
model needs a captured SQL baseline. See the [SQL baseline upgrade](README.md#sql-baselines-and-existing-notebooks)
for older publications that need a one-time capture.

Edit `pricing_models/burn_cost/monitoring.py`:

1. Set its runtime module, expected destination database and deployment slot.
2. Implement `load_dataset()` using the current source query. It returns a
   `PricingDataset` with the source name, unique row keys and its as-at column.
   Use a stable row order in the query. Any custom enrichment belongs here too.
3. Enable remote writes after checking the destination. Run notebook 07 once
   and inspect its runs, metrics, compatibility issues and categorical drift.

The loader is deliberately unconfigured in a new scaffold. It raises an error
pointing to the function to edit. It never silently reloads 01's local dataset.
The as-at comes from the new dataset, not the scheduled execution date.
The shared workflow gets the target, feature order, weights, offset and declared
transforms from the SQL baseline. No second PricingModelSpec is needed.

Automatic challenger publication supports the notebook's exported offset factor
and models without an offset. The legacy `ALREADY_APPLIED_SQL_EXPOSURE` contract
is checked before fitting and stops this workflow with an explanation. Its
observation-only monitoring calls remain available.

## A changed feature set stays a challenger

01 reads the new source column. In 02, configure that feature and save the recipe.
03 fits and publishes it as a challenger with the corresponding model version.
It stays a challenger until someone explicitly promotes it in 06.

07 and `monitoring.py` currently load the champion in their configured deployment
slot. Running 07 after publishing a new recipe does not test that challenger;
it continues to use the existing champion. There is not yet a notebook option
for testing the four variants against a selected, undeployed package.

Add a new feature to both 01's source query and the recurring loader when you
prepare the model for monitoring. The recurring runner reads fresh data
independently of 01's saved dataset.

## Test the file before scheduling

Use the same interpreter and account the scheduler will use. From a terminal:

```bash
uv run python pricing_models/burn_cost/monitoring.py
```

The script resolves project paths from its own location. It also works with an
absolute file path from another working directory. It creates one UTC-dated log
per invocation under `pricing_models/burn_cost/.local/monitoring_logs/` and prints
that path. Logs contain progress, SQL observation IDs and tracebacks on failure.
The notebook shows errors directly so you can follow the normal Python traceback.

| Exit code | Meaning |
|---|---|
| `0` | Four observations and three challenger packages are available in SQL |
| `1` | Configuration, data, fitting or persistence failed; inspect the log |
| `2` | The script could not create its log; the workflow did not start |
| `130` | The process was interrupted |

## Windows Task Scheduler

Create a task with your chosen weekly trigger and a **Start a program** action.
For a project at `C:\Pricing\burn_cost_project`, use:

| Action field | Value |
|---|---|
| Program/script | `C:\Pricing\burn_cost_project\.venv\Scripts\python.exe` |
| Add arguments | `-u "C:\Pricing\burn_cost_project\pricing_models\burn_cost\monitoring.py"` |
| Start in | `C:\Pricing\burn_cost_project` |

These fields select the executable, its arguments and its working directory.
See Microsoft's [execution action](https://learn.microsoft.com/en-us/windows/win32/taskschd/execaction)
and [working directory](https://learn.microsoft.com/en-us/windows/win32/taskschd/execaction-workingdirectory)
documentation.

Use an account that can read the source data, publish challenger packages and write
the log directory. Choose **Do not start a new instance** for overlapping runs.
Run the task manually once and check its Last Run Result and the new log file.
The machine must be available at execution time. Configure missed-run behavior
and retries to match the source refresh schedule.

## Cron under WSL

Use `crontab -e` and add a line such as this Monday 06:00 example, replacing both
paths with your project paths:

```cron
0 6 * * 1 /home/analyst/burn_cost_project/.venv/bin/python -u /home/analyst/burn_cost_project/pricing_models/burn_cost/monitoring.py
```

Cron has a limited environment, so use absolute interpreter and script paths.
The five fields above are minute, hour, day of month, month and day of week.
See [crontab(5)](https://man7.org/linux/man-pages/man5/crontab.5.html).
WSL must be running and its cron service enabled. Test the exact command under
the scheduled account before relying on the weekly trigger.

## Retries and model changes

Use the same SuperGLM version and Python major/minor version as the saved
baseline. Keep package upgrades separate from the scheduled command.

All fits must succeed before any monitoring observation is written. SQL writes
remain transactional per observation: a later write failure can leave earlier
successful observations. An exact retry reuses matching evidence. Each completed challenger publication is linked to its observation, so an exact
retry reuses its package too. Different fit evidence for an existing observation
raises rather than replacing it.

Notebook and script runs using the same model directory share a file lock. This
serializes their fits. Separate machines do not share that lock; the existing
SQL identity, deployment and retry checks still apply. Persistence rechecks the
deployment so a changed baseline cannot receive stale results.

Inspect candidates and the current champion through `pricing.V_MODEL_REGISTRY`.
It shows the model name, role, definition revision, refit type, dataset date and
publication time. The definition revision stays the same across weekly refits;
each result has its own package and run IDs. Former champions keep that label
after replacement. Filter `deployment_slot` when a model has several slots.
Inspect comparison evidence through `pricing.V_MODEL_MONITORING_RUN`,
`pricing.V_MODEL_MONITORING_RELATIVITY` and `pricing.V_MODEL_MONITORING_LAMBDA`.
Loss metrics are in `mlops.MODEL_MONITOR_METRIC`, linked by `monitor_run_id`.
No task is registered with the operating system by scaffolding or running 07.

## Review and promote

The champion is the package in the current deployment slot. There is one champion
per model and slot. A challenger becomes champion only through explicit deployment.

Notebook 06 lists published packages in one table with their Model version, Role,
fit type and dates. Set `PACKAGE_VERSION` from the Package column after reading
the list. Its SQL-only review shows the selected package, dated dataset, fit
metrics and current champion. The promotion cell uses that reviewed package and
your deployment reason.

Each metric row shows its package number and `Current champion?` status for
the selected slot at review time. For a weekly challenger, "Champion used for
this comparison" identifies the champion it was built against. That package
may have been replaced since then; its recorded scores remain attached to it.
The summary shows the current champion's package number separately. The full
`reviewed.summary` and `reviewed.metrics` results retain their SQL field names,
including `is_current_champion`.

The equivalent Python calls are:

```python
from pricing_pipeline.notebook import (
    deploy_model_version, list_challengers, review_model_version,
)

display(list_challengers(pricing, model=model))
reviewed = review_model_version(pricing, model=model, package_version=7)
display(reviewed.summary)
display(reviewed.metrics)
# Run after reviewing the selected package.
deployment = deploy_model_version(
    pricing, package=reviewed, reason="Approved after reviewing the weekly comparisons",
)
```

Promotion selects the saved package without refitting it. It checks that the
champion is still the deployment you reviewed. If another deployment occurred,
review again before promoting. Initial promotion works when the slot is empty.
The next weekly run automatically loads the new champion from SQL.

A promoted frozen refit retains the original choices about which lambdas and
knots may change in future. Its fitted coefficients and geometry become the new
baseline, without turning temporary freeze controls into permanent model settings.

The weekly publisher removes its temporary model, receipt and workbook files
after saving the SQL snapshot. Review, promotion and later refits use SQL. These
weekly packages do not retain the local model files required by the older editor
workflow. The observation metrics describe the fresh monitoring dataset; they
are not a new cross-validation run.

Existing projects keep their edited06 notebook when scaffolding again. Replace
its `load_model_version` call with `review_model_version` and display `.summary`
and `.metrics` to adopt SQL-only review, or copy the new 06 template into a separate
file. Completed 01/02 notebooks need no edits.
