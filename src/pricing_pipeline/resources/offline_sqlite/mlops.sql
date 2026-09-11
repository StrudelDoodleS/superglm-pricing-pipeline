CREATE TABLE IF NOT EXISTS mlops.MODEL_RUN_DATASET (
/*
Purpose: Link a recorded model run to datasets by their role.
One row: One model run, dataset role, and manifest reference.
Use: Current builds record the training role. The training link must agree with MODEL_RUN.manifest_id; the redundancy-check view reports disagreement.
*/
    model_run_id TEXT NOT NULL,
    manifest_id TEXT NOT NULL,
    dataset_role TEXT NOT NULL,
    PRIMARY KEY (model_run_id, dataset_role, manifest_id)
);

CREATE TABLE IF NOT EXISTS mlops.MODEL_RUN_SPLIT_SET (
/*
Purpose: Link a model run to the validation split used for a dataset.
One row: One split-set reference and split role for a model run.
Use: This is the SQL Server source of run-to-split lineage. Current builds use training and validation roles.
*/
    model_run_id TEXT NOT NULL,
    manifest_id TEXT NOT NULL,
    split_set_id TEXT NOT NULL,
    dataset_role TEXT NOT NULL,
    split_role TEXT NOT NULL,
    PRIMARY KEY (model_run_id, split_set_id, split_role)
);

CREATE TABLE IF NOT EXISTS mlops.MODEL_RUN_METRIC (
/*
Purpose: Store run-level model performance measurements.
One row: One named metric and optional scope for a model run.
Use: Scope cv contains held-out scores. Scope full_fit contains full-training diagnostics named fit_*. Missing diagnostics have no row. Fold-level measurements are stored separately in CV_FOLD_METRIC.
*/
    model_run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_scope TEXT,
    PRIMARY KEY (model_run_id, metric_name)
);
