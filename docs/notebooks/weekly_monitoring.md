# Run weekly challengers and promote a champion

Schedule `pricing_models/<model>/monitoring.py` using the Python interpreter from
your project environment. Notebook `07_model_monitoring.ipynb` calls the same
`run()` function so you can test the workflow interactively first.

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

## Configure once

After installing the package update, rerun your original `pricing-pipeline
scaffold` command without `--force`. It adds 07 and monitoring.py and preserves
your existing files, including completed 01/02 notebooks. For example:

```bash
uv run pricing-pipeline scaffold --model-name BURN_COST --target-name burn_cost --package-name burn_cost
```

Keep your model name, package name and deployment slot consistent with the
existing project. The database needs migrations through V050, and the deployed
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

Inspect candidates and the current champion through `pricing.V_MODEL_CHALLENGER`.
Inspect comparison evidence through `pricing.V_MODEL_MONITORING_RUN`,
`pricing.V_MODEL_MONITORING_RELATIVITY` and `pricing.V_MODEL_MONITORING_LAMBDA`.
Loss metrics are in `mlops.MODEL_MONITOR_METRIC`, linked by `monitor_run_id`.
No task is registered with the operating system by scaffolding or running 07.

## Review and promote

The champion is the package in the current deployment slot. There is one champion
per model and slot. A challenger becomes champion only through explicit deployment.

Notebook 06 lists published versions and their monitoring origins. Set
`PACKAGE_VERSION` to the version you want to review. Its SQL-only review shows
the selected version, dated dataset, fit metrics and current champion. The next
cell promotes that reviewed version with your deployment reason.

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
