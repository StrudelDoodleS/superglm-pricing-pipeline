# Burn-cost SQL Server demo

These are filled notebooks with synthetic Tweedie data, groupings, special levels,
splines, model publication, human champion selection and weekly refits.
Use the same Python environment that generated this directory. Install the
library's `demo` extra in that environment for the SQL driver and notebook tools.
The commands below already select that interpreter; this directory does not
create a separate Python environment.

## Prepare SQL Server

Start Docker Desktop with Linux containers, or Docker Engine with Compose.
The Microsoft SQL Server image requires an Intel/AMD x86-64 host and at least
2 GB of memory for SQL Server. See Microsoft's
[container requirements](https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-ver16).

Run:

```sh
__SETUP_COMMAND__
```

The script starts the included SQL Server 2022 Developer container, creates
`PricingNotebookDemo`, applies the package migrations and seeds two synthetic
source snapshots. It generates a password in `.env` and binds the SQL port to
localhost. Docker downloads the server image on the first run. Running setup
accepts Microsoft's SQL Server container licence through `ACCEPT_EULA=Y`.

Rerunning setup preserves source rows, saved models and credentials. Stop the
container without removing its data using:

```sh
__STOP_COMMAND__
```

The setup registers the **Pricing SQL demo** kernel. Select it in VS Code, or run:

```sh
__JUPYTER_COMMAND__
```

## Run the notebooks

Open `pricing_models/burn_cost_demo`.

| Notebook | Result |
|---|---|
| 01 | Read the older SQL snapshot and save the dataset for fitting. |
| 02 | Experiment locally and save the chosen model configuration to `prototype.toml`. |
| 03 | Fit, validate and publish the model package and recipe to SQL. |
| 06 | List packages, choose one, review it and explicitly make it champion in the demo slot. |
| 07 | Read the newer SQL snapshot, score the champion and save three refitted challengers. |
| 08 | Inspect SQL tables and views, compressed recipes and metrics; export rows to Excel. |

04 and 05 are optional edits. Run 06's promotion cell only after choosing a package
and entering your reason. A fresh database has no champion, so 07 needs that first
deployment. The demo does not automatically approve a model for you.

`Model version` identifies the declared recipe. `Package` identifies a saved
rating result. Weekly refits keep the model version; promotion changes the role.
The older `model_version`/`fit_version` SQL field is a separate internal fit counter
and is omitted from the review tables.

## A changed feature set stays a challenger

Add the source column in 01, configure the feature in 02 and save the recipe,
then run 03 to fit and publish it. This creates a challenger with the new recipe
and model version. It does not replace the champion, and it can stay a challenger.

07 currently uses the champion in its configured slot. Publishing the new
recipe in 03 alone does not make 07 test it. Selecting an undeployed challenger
for the four monitoring variants is not yet exposed in the notebook workflow.

When preparing the new model for recurring runs, include the new feature in
both 01's query and `monitoring.py`'s query. Weekly runs read fresh data and the
saved model state from SQL; they do not read 01's dataset file or `prototype.toml`.

## Inspect the database

Use server `127.0.0.1` and the `DEMO_SQL_PORT` from `.env`, database
`PricingNotebookDemo`, SQL login `sa`, and the generated password in `.env`.
The source table is `dbo.DEMO_BURN_COST_SOURCE`. The demo runtime only allows the
demo database and `master` for database creation.

`pricing.V_MODEL_REGISTRY` shows the packages and their roles per slot.
`pricing.MODEL_RECIPE` stores `recipe_gzip`. Its `recipe_json` column decompresses
the document when selected and does not store another copy.
