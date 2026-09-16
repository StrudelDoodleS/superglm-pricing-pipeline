# Python module index

Use this page to find the owner of a change. Each link opens the module; its
docstring explains the inputs, outputs or neighboring owners. For the execution
order, read [How the package fits together](package-flows.md).

Analysts normally import from `pricing_pipeline.notebook` or
`pricing_pipeline.reporting`. The files below describe implementation ownership;
they are not a list of additional public APIs.

## Entry points

| Module | Purpose |
|---|---|
| [__init__.py](../src/pricing_pipeline/__init__.py) | Fit pricing models, save their evidence and rating tables, and deploy to SQL. |
| [__main__.py](../src/pricing_pipeline/__main__.py) | Run the installed CLI through `python -m pricing_pipeline`. |
| [cli.py](../src/pricing_pipeline/cli.py) | Parse `pricing-pipeline init`, `scaffold` and `demo` commands. |
| [demo.py](../src/pricing_pipeline/demo.py) | Copy the filled notebooks and local SQL Server setup from installed demo resources. |
| [notebook.py](../src/pricing_pipeline/notebook.py) | Public Python entry points for the pricing-model workflow. |

## Data and validation

| Module | Purpose |
|---|---|
| [data/__init__.py](../src/pricing_pipeline/data/__init__.py) | Identify datasets and preserve the rows used for fitting and validation. |
| [data/dataset.py](../src/pricing_pipeline/data/dataset.py) | Keep a named dataframe snapshot with its source, row keys and as-at column. |
| [data/frame_artifact.py](../src/pricing_pipeline/data/frame_artifact.py) | Save, inspect and load a dataframe handoff between notebooks. |
| [data/fremtpl.py](../src/pricing_pipeline/data/fremtpl.py) | Fetch and prepare the freMTPL demonstration dataset. |
| [data/manifest.py](../src/pricing_pipeline/data/manifest.py) | Record which dataset rows, columns and validation splits a fit used. |
| [data/row_identity.py](../src/pricing_pipeline/data/row_identity.py) | Hash ordered row keys so saved split positions can be checked against data. |
| [data/split_artifacts.py](../src/pricing_pipeline/data/split_artifacts.py) | Write validation fold positions to NPZ files and calculate file hashes. |
| [data/transforms.py](../src/pricing_pipeline/data/transforms.py) | Declare and apply named dataframe transformations such as Log and Clip. |
| [data/validation.py](../src/pricing_pipeline/data/validation.py) | Describe analyst-supplied validation splitters for audit records. |

## Runtime and database setup

| Module | Purpose |
|---|---|
| [infra/__init__.py](../src/pricing_pipeline/infra/__init__.py) | Provide database connections, schema setup, settings and filesystem locks. |
| [infra/config.py](../src/pricing_pipeline/infra/config.py) | Load runtime settings and resolve project-relative artifact paths. |
| [infra/db.py](../src/pricing_pipeline/infra/db.py) | Build SQL Server engines and attach the pipeline's schema configuration. |
| [infra/file_lock.py](../src/pricing_pipeline/infra/file_lock.py) | Serialize local file operations with an exclusive advisory lock. |
| [infra/migrations.py](../src/pricing_pipeline/infra/migrations.py) | Apply the packaged SQL Server migration chain in version order. |
| [infra/offline_sqlite.py](../src/pricing_pipeline/infra/offline_sqlite.py) | Persistent attached-schema SQLite storage for local pricing workflows. |
| [infra/reset_schema.py](../src/pricing_pipeline/infra/reset_schema.py) | Drop and rebuild selected pipeline schemas after checking the destination. |
| [infra/runtime.py](../src/pricing_pipeline/infra/runtime.py) | Adapt environment settings or a project's `get_engine` module. |
| [infra/schema.py](../src/pricing_pipeline/infra/schema.py) | Validate SQL schema names and substitute them into pipeline SQL. |

## Model records

| Module | Purpose |
|---|---|
| [models/__init__.py](../src/pricing_pipeline/models/__init__.py) | Define model registration, validation and completed-build records. |
| [models/config.py](../src/pricing_pipeline/models/config.py) | Describe stable model registration and validation split choices. |
| [models/kinds.py](../src/pricing_pipeline/models/kinds.py) | Name and validate the origin of a saved model build. |
| [models/pricing.py](../src/pricing_pipeline/models/pricing.py) | Analyst model choices and the validation of their data-column roles. |
| [models/spec.py](../src/pricing_pipeline/models/spec.py) | Validate the immutable evidence passed from a completed fit to publication. |

## Fitting, monitoring and adjustments

| Module | Purpose |
|---|---|
| [modeling/__init__.py](../src/pricing_pipeline/modeling/__init__.py) | Fit models, preserve reusable configuration and run monitoring refits. |
| [modeling/level_grouping_artifact.py](../src/pricing_pipeline/modeling/level_grouping_artifact.py) | Save and reapply categorical groups chosen in the SuperGLM editor. |
| [modeling/manual_adjustment.py](../src/pricing_pipeline/modeling/manual_adjustment.py) | Describe and replay business adjustments to selected model relativities. |
| [modeling/scratch_benchmark.py](../src/pricing_pipeline/modeling/scratch_benchmark.py) | Disposable unconstrained and boosted-tree benchmarks for scratch notebooks. |
| [modeling/scratch_diagnostics.py](../src/pricing_pipeline/modeling/scratch_diagnostics.py) | Held-out diagnostics for governed GAM/GBM scratch comparisons. |
| [modeling/standard_superglm.py](../src/pricing_pipeline/modeling/standard_superglm.py) | Run validation and full fitting, then write a completed build's evidence. |

## Monitoring refits and evidence

| Module | Purpose |
|---|---|
| [modeling/monitoring/__init__.py](../src/pricing_pipeline/modeling/monitoring/__init__.py) | Controlled monitoring refits and their saved audit evidence. |
| [modeling/monitoring/batch.py](../src/pricing_pipeline/modeling/monitoring/batch.py) | Check and run four variants on one fresh dataset, save observations and optionally publish exact refits. |
| [modeling/monitoring/challengers.py](../src/pricing_pipeline/modeling/monitoring/challengers.py) | Export fitted challengers, publish their SQL state and remove temporary files. |
| [modeling/monitoring/baseline.py](../src/pricing_pipeline/modeling/monitoring/baseline.py) | Verify the saved baseline and bind a monitoring dataframe to its declared roles. |
| [modeling/monitoring/storage.py](../src/pricing_pipeline/modeling/monitoring/storage.py) | Capture baseline state at publication, load the current deployment from SQL and verify its source lineage. |
| [modeling/monitoring/snapshot.py](../src/pricing_pipeline/modeling/monitoring/snapshot.py) | Define and validate versioned JSON baseline state without training rows or Python object serialization. |
| [modeling/monitoring/snapshot_prediction.py](../src/pricing_pipeline/modeling/monitoring/snapshot_prediction.py) | Score the saved polynomial and categorical contributions and report static metrics. |
| [modeling/monitoring/snapshot_fitting.py](../src/pricing_pipeline/modeling/monitoring/snapshot_fitting.py) | Construct each controlled refit from the saved recipe, geometry and smoothing settings. |
| [modeling/monitoring/snapshot_validation.py](../src/pricing_pipeline/modeling/monitoring/snapshot_validation.py) | Reject incompatible formats, versions and contradictory snapshot evidence before scoring or fitting. |
| [modeling/monitoring/contracts.py](../src/pricing_pipeline/modeling/monitoring/contracts.py) | Records, variant policies and canonical values used by monitoring. |
| [modeling/monitoring/data_checks.py](../src/pricing_pipeline/modeling/monitoring/data_checks.py) | Check monitoring inputs and compare categorical mixes before any model refit. |
| [modeling/monitoring/domains.py](../src/pricing_pipeline/modeling/monitoring/domains.py) | Read saved feature domains for SQL preflight without reconstructing fitted models. |
| [modeling/monitoring/support_checks.py](../src/pricing_pipeline/modeling/monitoring/support_checks.py) | Check effective numeric and ordered spline support before estimating monitoring coefficients. |
| [modeling/monitoring/evidence.py](../src/pricing_pipeline/modeling/monitoring/evidence.py) | Extract monitoring terms, smoothing parameters, relativities and loss metrics. |
| [modeling/monitoring/fitting.py](../src/pricing_pipeline/modeling/monitoring/fitting.py) | Capture baseline structure and reconstruct the model allowed by a monitoring variant. |
| [modeling/monitoring/invariants.py](../src/pricing_pipeline/modeling/monitoring/invariants.py) | Verify the structural restrictions and canonical evidence of a monitoring fit. |
| [modeling/monitoring/persistence.py](../src/pricing_pipeline/modeling/monitoring/persistence.py) | Save a verified monitoring observation and recover identical concurrent retries. |
| [modeling/monitoring/workflow.py](../src/pricing_pipeline/modeling/monitoring/workflow.py) | Run one monitoring comparison through its explicit verification and fitting steps. |

## Editable model recipes

| Module | Purpose |
|---|---|
| [modeling/recipes/__init__.py](../src/pricing_pipeline/modeling/recipes/__init__.py) | Portable declared recipes with no database or fitting side effects. |
| [modeling/recipes/io.py](../src/pricing_pipeline/modeling/recipes/io.py) | Read and write editable model recipes as TOML. |
| [modeling/recipes/schema.py](../src/pricing_pipeline/modeling/recipes/schema.py) | Immutable declared model configuration and exact semantic identity. |
| [modeling/recipes/superglm.py](../src/pricing_pipeline/modeling/recipes/superglm.py) | Supported SuperGLM constructor settings for saving and loading recipes. |

## Remote build handoffs

| Module | Purpose |
|---|---|
| [orchestration/__init__.py](../src/pricing_pipeline/orchestration/__init__.py) | Verify completed remote builds before handing them to publication. |
| [orchestration/pipeline.py](../src/pricing_pipeline/orchestration/pipeline.py) | Check a completed export against its workbook and registered model. |
| [orchestration/publish_completed_build.py](../src/pricing_pipeline/orchestration/publish_completed_build.py) | Verify a completed build's artifacts and SQL lineage before remote save. |

## Package publication and deployment

| Module | Purpose |
|---|---|
| [publishing/__init__.py](../src/pricing_pipeline/publishing/__init__.py) | Turn completed builds into SQL rating packages and deploy selected packages. |
| [publishing/monitoring.py](../src/pricing_pipeline/publishing/monitoring.py) | Verify immutable links between sealed monitoring observations and published challengers. |
| [publishing/deployment.py](../src/pricing_pipeline/publishing/deployment.py) | Activate a published rating package in a model's deployment slot. |
| [publishing/editor.py](../src/pricing_pipeline/publishing/editor.py) | Verify editor or manual changes and publish them as a child package. |
| [publishing/editor_contracts.py](../src/pricing_pipeline/publishing/editor_contracts.py) | Records and submission identity shared by the edit publication stages. |
| [publishing/editor_export.py](../src/pricing_pipeline/publishing/editor_export.py) | Export a verified edited model and compare it with its parent and champion. |
| [publishing/editor_parent.py](../src/pricing_pipeline/publishing/editor_parent.py) | Load and verify an editor submission's saved parent and deployed comparison model. |
| [publishing/editor_replay.py](../src/pricing_pipeline/publishing/editor_replay.py) | Load submitted edits and verify them by replaying the recorded intent. |
| [publishing/editor_retry.py](../src/pricing_pipeline/publishing/editor_retry.py) | Verify exact retries and equivalent editor publications against stored lineage. |
| [publishing/identity.py](../src/pricing_pipeline/publishing/identity.py) | Identify registered models, exact retries and equivalent publications. |
| [publishing/lineage.py](../src/pricing_pipeline/publishing/lineage.py) | Write the provenance attached to a published model run. |
| [publishing/metadata.py](../src/pricing_pipeline/publishing/metadata.py) | Describe fitted SuperGLM terms in a verifiable publication receipt. |
| [publishing/publish.py](../src/pricing_pipeline/publishing/publish.py) | Validate a publication request and select its database writer. |
| [publishing/rating_tables.py](../src/pricing_pipeline/publishing/rating_tables.py) | Export and parse the workbook used to publish model relativities. |
| [publishing/recipes.py](../src/pricing_pipeline/publishing/recipes.py) | Allocate and verify recipe revisions within a publication transaction. |
| [publishing/spline_segments.py](../src/pricing_pipeline/publishing/spline_segments.py) | Validate the polynomial segments used for exact spline relativities. |
| [publishing/sqlite.py](../src/pricing_pipeline/publishing/sqlite.py) | Save prepared rating tables and audit records in one SQLite transaction. |
| [publishing/sqlserver.py](../src/pricing_pipeline/publishing/sqlserver.py) | Save prepared rating tables and audit records in one SQL Server transaction. |

## Saved-model review and edit submissions

| Module | Purpose |
|---|---|
| [workbench/__init__.py](../src/pricing_pipeline/workbench/__init__.py) | Load saved model versions for review and retain proposed edits. |
| [workbench/artifacts.py](../src/pricing_pipeline/workbench/artifacts.py) | Save and verify the fitted-model files attached to a saved version. |
| [workbench/core.py](../src/pricing_pipeline/workbench/core.py) | List saved packages and load one with its verified model artifacts. |
| [workbench/submission.py](../src/pricing_pipeline/workbench/submission.py) | Save an editor session and its evidence for replay during publication. |

## Reports from existing predictions

| Module | Purpose |
|---|---|
| [reporting/__init__.py](../src/pricing_pipeline/reporting/__init__.py) | Create offline model-comparison reports from existing predictions. |
| [reporting/_underwriter_html.py](../src/pricing_pipeline/reporting/_underwriter_html.py) | Self-contained HTML shell for the underwriter report. |
| [reporting/_underwriter_styles.py](../src/pricing_pipeline/reporting/_underwriter_styles.py) | Define the CSS embedded in the standalone underwriter HTML report. |
| [reporting/diagnostics.py](../src/pricing_pipeline/reporting/diagnostics.py) | Side-effect-free aggregate diagnostics for already-scored predictions. |
| [reporting/evidence.py](../src/pricing_pipeline/reporting/evidence.py) | Collect model evidence and normalize it before report calculations. |
| [reporting/evidence_types.py](../src/pricing_pipeline/reporting/evidence_types.py) | Records and declared limits shared by report adapters and evidence validation. |
| [reporting/evidence_values.py](../src/pricing_pipeline/reporting/evidence_values.py) | Validate scalar values, reporting context and category identities in model evidence. |
| [reporting/inputs.py](../src/pricing_pipeline/reporting/inputs.py) | Validate and align the data supplied to a model-comparison report. |
| [reporting/interaction_evidence.py](../src/pricing_pipeline/reporting/interaction_evidence.py) | Normalize interaction coordinates, reporting support and plot metadata. |
| [reporting/movement.py](../src/pricing_pipeline/reporting/movement.py) | Privacy-safe aggregate comparisons of model prediction movement. |
| [reporting/report.py](../src/pricing_pipeline/reporting/report.py) | Build an offline HTML report from validated predictions and model evidence. |

## Model evidence adapters

| Module | Purpose |
|---|---|
| [reporting/adapters/__init__.py](../src/pricing_pipeline/reporting/adapters/__init__.py) | Translate model-specific artifacts into the reporting evidence types. |
| [reporting/adapters/rating_workbook.py](../src/pricing_pipeline/reporting/adapters/rating_workbook.py) | Evidence adapter for exported SuperGLM rating-table workbooks. |
| [reporting/adapters/superglm.py](../src/pricing_pipeline/reporting/adapters/superglm.py) | SuperGLM-specific evidence extraction for aggregate reports. |

## Project and notebook generation

| Module | Purpose |
|---|---|
| [scaffold/__init__.py](../src/pricing_pipeline/scaffold/__init__.py) | Generate notebooks from CLI arguments or explicit Python options. |
| [scaffold/commands.py](../src/pricing_pipeline/scaffold/commands.py) | Implement CLI init and scaffold requests using resolved project options. |
| [scaffold/config.py](../src/pricing_pipeline/scaffold/config.py) | Parse scaffold TOML and validate the options used to generate notebooks. |
| [scaffold/render.py](../src/pricing_pipeline/scaffold/render.py) | Render installed notebook templates with validated model options. |
| [scaffold/service.py](../src/pricing_pipeline/scaffold/service.py) | Create the model directory and write rendered notebook files. |

## Installed resource access

| Module | Purpose |
|---|---|
| [resources/__init__.py](../src/pricing_pipeline/resources/__init__.py) | Locate SQL and notebook resources shipped in the installed distribution. |

## Installed scaffold resources

| Module | Purpose |
|---|---|
| [resources/scaffold/__init__.py](../src/pricing_pipeline/resources/scaffold/__init__.py) | Ship the default project TOML, builder/developer agents, seven notebooks and the weekly monitoring module. |

## Developer tools

| Module | Purpose |
|---|---|
| [tools/__init__.py](../src/pricing_pipeline/tools/__init__.py) | Support repository maintenance tasks outside the notebook model workflow. |
| [tools/db_diagrams.py](../src/pricing_pipeline/tools/db_diagrams.py) | Read database metadata and generate a browsable SQL schema diagram. |

The generated `monitoring.py` calls `notebook.run_monitoring`.
[`monitoring_runner.py`](../src/pricing_pipeline/monitoring_runner.py) supplies
logs and process exit codes for direct script execution.
[`workbench/champion.py`](../src/pricing_pipeline/workbench/champion.py) reads
SQL-only package reviews and binds promotion to the current deployment seen
during review.
