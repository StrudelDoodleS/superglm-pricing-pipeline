CREATE TABLE IF NOT EXISTS pricing.FREMTPL_RAW (
/*
Purpose: Hold the public freMTPL motor claim frequency data for demonstrations.
One row: One source policy record, including claim count and exposure in years.
Use: This is demo input. Production model lineage uses DATASET_MANIFEST and the model-frame artifact.
*/
    IDpol INTEGER NOT NULL PRIMARY KEY,
    ClaimNb INTEGER NOT NULL,
    Exposure REAL NOT NULL,
    Area TEXT,
    VehPower INTEGER,
    VehAge INTEGER,
    DrivAge INTEGER,
    BonusMalus INTEGER,
    VehBrand TEXT,
    VehGas TEXT,
    Density REAL,
    Region TEXT
);

CREATE TABLE IF NOT EXISTS pricing.DATASET_MANIFEST (
/*
Purpose: Identify the exact dataset snapshot used for a model or monitoring observation.
One row: One dataset version, with its data-as-at date, row count, column roles, and content hashes.
Use: Data-as-at describes source completeness. It is separate from the import or fit time. Source records live in the model-frame artifact.
*/
    manifest_id TEXT NOT NULL PRIMARY KEY,
    manifest_signature_sha256 TEXT,
    dataset_name TEXT NOT NULL,
    source_system TEXT,
    data_as_of_date TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    pk_columns_json TEXT NOT NULL,
    target_column TEXT,
    weight_column TEXT,
    model_frame_sha256 TEXT NOT NULL,
    frame_hash_metadata_json TEXT NOT NULL,
    exposure_column TEXT,
    data_as_of_column TEXT,
    offset_column TEXT,
    offset_source_column TEXT,
    offset_label TEXT,
    export_weight_column TEXT,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing.DATASET_COLUMN (
/*
Purpose: Describe columns in a recorded dataset snapshot.
One row: One column within a dataset manifest, with its role, type, and summary statistics.
Use: Use this to check the model inputs without loading policy records.
*/
    manifest_id TEXT NOT NULL,
    ordinal_no INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    column_role TEXT NOT NULL,
    pandas_dtype TEXT NOT NULL,
    null_count INTEGER NOT NULL,
    distinct_count INTEGER,
    PRIMARY KEY (manifest_id, ordinal_no)
);

CREATE TABLE IF NOT EXISTS pricing.CV_SPLIT_SET (
/*
Purpose: Identify how a dataset was split for validation.
One row: One split configuration and ordered-row identity for one manifest.
Use: Exact row membership comes from replaying the recorded configuration or loading its verified split artifact.
*/
    split_set_id TEXT NOT NULL PRIMARY KEY,
    manifest_id TEXT NOT NULL,
    split_mode TEXT NOT NULL,
    splitter_class TEXT,
    splitter_params_json TEXT,
    row_order_sha256 TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    fold_count INTEGER NOT NULL,
    groups_column TEXT,
    stratify_column TEXT,
    artifact_uri TEXT,
    artifact_sha256 TEXT,
    runtime_metadata_json TEXT,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pricing.CV_FOLD (
/*
Purpose: Record the size of each validation split.
One row: One fold number within a split set, with training and test row counts.
Use: This table contains counts, not individual row membership. A holdout also has a fold record.
*/
    split_set_id TEXT NOT NULL,
    fold_no INTEGER NOT NULL,
    n_train INTEGER NOT NULL,
    n_test INTEGER NOT NULL,
    PRIMARY KEY (split_set_id, fold_no)
);

CREATE TABLE IF NOT EXISTS pricing.CV_FOLD_METRIC (
/*
Purpose: Store predictive performance measured on each held-out fold.
One row: One metric for one model run, split set, and fold.
Use: Compare runs on the same split set. These results differ from full-sample training metrics and pooled validation metrics.
*/
    model_run_id TEXT NOT NULL,
    split_set_id TEXT NOT NULL,
    fold_no INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    PRIMARY KEY (model_run_id, split_set_id, fold_no, metric_name)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_MODEL (
/*
Purpose: Register a named business model, such as motor claim frequency.
One row: One stable model identity, target, label, and active or retired status.
Use: Versions belong to MODEL_RUN and PRICING_RATE_PACKAGE. An active model is not necessarily deployed.
*/
    model_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    model_label TEXT,
    target_name TEXT NOT NULL,
    model_type TEXT NOT NULL,
    model_status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    retired_ts TEXT,
    UNIQUE (model_name)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_MODEL_VERSION_RESERVATION (
/*
Purpose: Allocate model version names safely when builds run concurrently.
One row: One reserved model version for a model and export identifier.
Use: Internal allocation record. Do not infer publication or deployment from a reservation.
*/
    model_id INTEGER NOT NULL,
    export_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    reserved_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_id, export_id),
    UNIQUE (model_id, model_version)
);

CREATE TABLE IF NOT EXISTS pricing.MODEL_RECIPE (
/*
Purpose: Store the declared modelling choices shared by builds of one registered model.
One row: One immutable canonical recipe and automatically allocated model-scoped revision.
Use: MODEL_RUN links successful builds. Dataset dates, bindings and execution settings remain build evidence.
*/
    recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL REFERENCES PRICING_MODEL(model_id),
    recipe_revision INTEGER NOT NULL CHECK (recipe_revision > 0),
    recipe_sha256 TEXT NOT NULL CHECK (length(recipe_sha256)=64 AND recipe_sha256 NOT GLOB '*[^0-9a-f]*'),
    recipe_format_version INTEGER NOT NULL CHECK (recipe_format_version = 1),
    recipe_json TEXT NOT NULL CHECK (json_valid(recipe_json) AND json_type(recipe_json)='object'),
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    UNIQUE (model_id, recipe_revision),
    UNIQUE (model_id, recipe_sha256),
    UNIQUE (model_id, recipe_id)
);

CREATE TABLE IF NOT EXISTS pricing.MODEL_RUN (
/*
Purpose: Record a model build or an edited revision and its audit evidence.
One row: One recorded run with its model, training manifest, package, parent, status, and artifact hashes.
Use: model_kind distinguishes RAW, ROUTINE_EDIT, EDITOR_EDIT, and MANUAL_EDIT. Publication and deployment are separate steps.
*/
    model_run_id TEXT PRIMARY KEY,
    parent_model_run_id TEXT,
    model_id INTEGER NOT NULL,
    dag_id TEXT,
    airflow_run_id TEXT,
    mlflow_run_id TEXT,
    model_version TEXT NOT NULL,
    model_kind TEXT NOT NULL DEFAULT 'RAW'
        CHECK (model_kind IN ('RAW', 'ROUTINE_EDIT', 'EDITOR_EDIT', 'MANUAL_EDIT')),
    model_equivalence_sha256 TEXT,
    recipe_id INTEGER,
    recipe_status TEXT NOT NULL DEFAULT 'LEGACY',
    recipe_unavailable_reason TEXT,
    export_id TEXT NOT NULL,
    manifest_id TEXT NOT NULL,
    split_set_id TEXT,
    rate_package_id INTEGER NOT NULL,
    model_name TEXT,
    rating_workbook_path TEXT NOT NULL,
    rating_workbook_sha256 TEXT NOT NULL,
    publication_receipt_path TEXT,
    publication_receipt_sha256 TEXT,
    model_artifact_path TEXT,
    candidate_artifact_path TEXT,
    candidate_artifact_sha256 TEXT,
    candidate_artifact_format TEXT,
    candidate_artifact_size_bytes INTEGER,
    candidate_python_version TEXT,
    candidate_superglm_version TEXT,
    model_source_sha256 TEXT,
    effective_from TEXT,
    run_status TEXT NOT NULL DEFAULT 'SUCCEEDED',
    started_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_ts TEXT,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    FOREIGN KEY (model_id, recipe_id) REFERENCES MODEL_RECIPE(model_id, recipe_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS pricing.UX_MODEL_RUN_RATE_PACKAGE
ON MODEL_RUN(rate_package_id)
WHERE rate_package_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS pricing.PRICING_RATE_PACKAGE (
/*
Purpose: Store the header of an immutable version of a rating model.
One row: One package revision with a base rate, status, validity dates, and optional parent package.
Use: Local publication records LOCAL_AUDIT packages and workbook evidence. Editor publication and deployment require the SQL Server workflow.
*/
    rate_package_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_rate_package_id INTEGER,
    model_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    package_version INTEGER NOT NULL,
    base_rate REAL NOT NULL,
    effective_from_date TEXT,
    effective_to_date TEXT,
    package_status TEXT NOT NULL,
    source_export_id TEXT,
    source_file TEXT,
    publication_receipt_json TEXT,
    publication_receipt_sha256 TEXT,
    staging_content_sha256 TEXT,
    package_metadata_json TEXT,
    revision_metadata_json TEXT,
    offset_handling TEXT NOT NULL DEFAULT 'UNKNOWN',
    offset_factor_name TEXT,
    offset_source_name TEXT,
    offset_label TEXT,
    metadata_origin TEXT,
    manifest_id TEXT,
    split_set_id TEXT,
    rating_workbook_path TEXT,
    model_artifact_path TEXT,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    UNIQUE (model_id, source_export_id),
    UNIQUE (model_id, package_version)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_MODEL_DEPLOYMENT (
/*
Purpose: Record which rating package serves each model and deployment slot over time.
One row: One deployment interval for a model, slot, and package.
Use: The row with effective_to_ts IS NULL is current. Closed rows retain deployment history; a package can be deployed more than once.
*/
    deployment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    rate_package_id INTEGER NOT NULL,
    deployment_slot TEXT NOT NULL,
    effective_from_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    effective_to_ts TEXT,
    deployed_by TEXT NOT NULL,
    deployment_note TEXT,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (effective_to_ts IS NULL OR effective_to_ts > effective_from_ts),
    FOREIGN KEY (model_id) REFERENCES PRICING_MODEL(model_id),
    FOREIGN KEY (rate_package_id) REFERENCES PRICING_RATE_PACKAGE(rate_package_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS pricing.UX_MODEL_DEPLOYMENT_CURRENT
ON PRICING_MODEL_DEPLOYMENT(model_id, deployment_slot)
WHERE effective_to_ts IS NULL;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_DEPLOYMENT_PACKAGE_GUARD_INSERT
BEFORE INSERT ON PRICING_MODEL_DEPLOYMENT
WHEN NOT EXISTS (
    SELECT 1
    FROM PRICING_RATE_PACKAGE AS package
    WHERE package.rate_package_id = NEW.rate_package_id
      AND package.model_id = NEW.model_id
      AND package.package_status = 'PUBLISHED'
)
BEGIN
    SELECT RAISE(
        ABORT,
        'deployment package must exist, match model_id, and be PUBLISHED'
    );
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_DEPLOYMENT_PACKAGE_GUARD_UPDATE
BEFORE UPDATE OF model_id, rate_package_id ON PRICING_MODEL_DEPLOYMENT
WHEN NOT EXISTS (
    SELECT 1
    FROM PRICING_RATE_PACKAGE AS package
    WHERE package.rate_package_id = NEW.rate_package_id
      AND package.model_id = NEW.model_id
      AND package.package_status = 'PUBLISHED'
)
BEGIN
    SELECT RAISE(
        ABORT,
        'deployment package must exist, match model_id, and be PUBLISHED'
    );
END;

-- SQL Server owns these logical tables in mlops.  The local mirror lives in
-- pricing.sqlite so its persistent monitoring views also work when that file
-- is opened without the attached-schema coordinator.
CREATE TABLE IF NOT EXISTS pricing.MODEL_MONITOR_VARIANT (
/*
Purpose: Define the four supported monitoring comparisons against a deployed model.
One row: One preset describing whether coefficients, smoothing penalties, and data-driven knots may change.
Use: These presets produce monitoring evidence, not deployable candidate packages.
*/
    variant_code TEXT NOT NULL PRIMARY KEY,
    variant_label TEXT NOT NULL,
    refit_coefficients INTEGER NOT NULL CHECK (refit_coefficients IN (0, 1)),
    reestimate_lambdas INTEGER NOT NULL CHECK (reestimate_lambdas IN (0, 1)),
    reposition_data_driven_knots INTEGER NOT NULL
        CHECK (reposition_data_driven_knots IN (0, 1)),
    structure_frozen INTEGER NOT NULL DEFAULT 1 CHECK (structure_frozen = 1),
    CHECK (
        variant_code IN (
            'STATIC_SCORE',
            'FROZEN_REFIT',
            'REESTIMATE_LAMBDA',
            'FULL_ADAPTIVE'
        )
    )
);

INSERT INTO pricing.MODEL_MONITOR_VARIANT (
    variant_code,
    variant_label,
    refit_coefficients,
    reestimate_lambdas,
    reposition_data_driven_knots,
    structure_frozen
) VALUES
    ('STATIC_SCORE', 'Deployed model, no refit', 0, 0, 0, 1),
    ('FROZEN_REFIT', 'Refit coefficients only', 1, 0, 0, 1),
    ('REESTIMATE_LAMBDA', 'Refit coefficients and REML lambdas', 1, 1, 0, 1),
    ('FULL_ADAPTIVE', 'Refit coefficients, lambdas, and data-driven knots', 1, 1, 1, 1)
ON CONFLICT(variant_code) DO NOTHING;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_VARIANT_IMMUTABLE_UPDATE
BEFORE UPDATE ON MODEL_MONITOR_VARIANT
BEGIN
    SELECT RAISE(ABORT, 'monitoring variant policy is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_VARIANT_IMMUTABLE_DELETE
BEFORE DELETE ON MODEL_MONITOR_VARIANT
BEGIN
    SELECT RAISE(ABORT, 'monitoring variant policy is immutable');
END;

CREATE TABLE IF NOT EXISTS pricing.MODEL_MONITORING_BASELINE (
/*
Purpose: Store the JSON fitted state and reference summaries used by recurring monitoring.
One row: One immutable publication capture, or an explicit unavailable reason, per successful model run.
Use: Load the current deployment through SQL. Historical runs can be captured once from verified artifacts without refitting.
*/
    model_run_id TEXT NOT NULL PRIMARY KEY REFERENCES MODEL_RUN(model_run_id),
    model_id INTEGER NOT NULL REFERENCES PRICING_MODEL(model_id),
    rate_package_id INTEGER NOT NULL REFERENCES PRICING_RATE_PACKAGE(rate_package_id),
    capture_status TEXT NOT NULL CHECK (capture_status IN ('CAPTURED', 'UNAVAILABLE')),
    unavailable_reason TEXT,
    snapshot_schema_version INTEGER,
    snapshot_json TEXT CHECK (snapshot_json IS NULL OR (json_valid(snapshot_json) AND json_type(snapshot_json)='object')),
    snapshot_sha256 TEXT CHECK (snapshot_sha256 IS NULL OR (length(snapshot_sha256)=64 AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*')),
    superglm_version TEXT,
    source_lineage_json TEXT NOT NULL CHECK (json_valid(source_lineage_json) AND json_type(source_lineage_json)='object'),
    source_lineage_sha256 TEXT NOT NULL CHECK (length(source_lineage_sha256)=64 AND source_lineage_sha256 NOT GLOB '*[^0-9a-f]*'),
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    CHECK (
        (capture_status='CAPTURED' AND unavailable_reason IS NULL
         AND snapshot_schema_version IS NOT NULL AND snapshot_schema_version>=1
         AND snapshot_json IS NOT NULL AND snapshot_sha256 IS NOT NULL AND superglm_version IS NOT NULL)
        OR (capture_status='UNAVAILABLE' AND unavailable_reason IS NOT NULL AND length(trim(unavailable_reason))>0
            AND snapshot_schema_version IS NULL AND snapshot_json IS NULL AND snapshot_sha256 IS NULL AND superglm_version IS NULL)
    )
);

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITORING_BASELINE_LINEAGE_INSERT
BEFORE INSERT ON MODEL_MONITORING_BASELINE
WHEN NOT EXISTS (
    SELECT 1 FROM MODEL_RUN AS mr JOIN PRICING_RATE_PACKAGE AS rp
      ON rp.rate_package_id=mr.rate_package_id AND rp.model_id=mr.model_id
    WHERE mr.model_run_id=NEW.model_run_id AND mr.model_id=NEW.model_id
      AND mr.rate_package_id=NEW.rate_package_id AND mr.run_status='SUCCESS'
      AND rp.package_status IN ('PUBLISHED', 'LOCAL_AUDIT')
)
BEGIN
    SELECT RAISE(ABORT, 'monitoring baseline must identify one successful published model run');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITORING_BASELINE_UPDATE
BEFORE UPDATE ON MODEL_MONITORING_BASELINE
BEGIN
    SELECT RAISE(ABORT, 'monitoring baselines are immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITORING_BASELINE_DELETE
BEFORE DELETE ON MODEL_MONITORING_BASELINE
BEGIN
    SELECT RAISE(ABORT, 'monitoring baselines are immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RUN_BASELINE_IDENTITY_UPDATE
BEFORE UPDATE ON MODEL_RUN
WHEN EXISTS (SELECT 1 FROM MODEL_MONITORING_BASELINE WHERE model_run_id=OLD.model_run_id)
AND (
    NEW.model_run_id IS NOT OLD.model_run_id OR NEW.model_id IS NOT OLD.model_id
    OR NEW.rate_package_id IS NOT OLD.rate_package_id OR NEW.run_status IS NOT OLD.run_status
    OR NEW.model_version IS NOT OLD.model_version OR NEW.model_kind IS NOT OLD.model_kind
    OR NEW.export_id IS NOT OLD.export_id OR NEW.manifest_id IS NOT OLD.manifest_id
    OR NEW.publication_receipt_sha256 IS NOT OLD.publication_receipt_sha256
    OR NEW.model_source_sha256 IS NOT OLD.model_source_sha256
    OR NEW.model_equivalence_sha256 IS NOT OLD.model_equivalence_sha256
    OR NEW.candidate_artifact_sha256 IS NOT OLD.candidate_artifact_sha256
    OR NEW.candidate_artifact_format IS NOT OLD.candidate_artifact_format
    OR NEW.candidate_artifact_size_bytes IS NOT OLD.candidate_artifact_size_bytes
    OR NEW.candidate_python_version IS NOT OLD.candidate_python_version
    OR NEW.candidate_superglm_version IS NOT OLD.candidate_superglm_version
    OR NEW.rating_workbook_sha256 IS NOT OLD.rating_workbook_sha256
)
BEGIN
    SELECT RAISE(ABORT, 'a model run referenced by a monitoring baseline retains its source identity');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RUN_BASELINE_IDENTITY_DELETE
BEFORE DELETE ON MODEL_RUN
WHEN EXISTS (SELECT 1 FROM MODEL_MONITORING_BASELINE WHERE model_run_id=OLD.model_run_id)
BEGIN
    SELECT RAISE(ABORT, 'a model run referenced by a monitoring baseline retains its source identity');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_RATE_PACKAGE_BASELINE_IDENTITY_UPDATE
BEFORE UPDATE ON PRICING_RATE_PACKAGE
WHEN EXISTS (SELECT 1 FROM MODEL_MONITORING_BASELINE WHERE rate_package_id=OLD.rate_package_id)
AND (
    NEW.rate_package_id IS NOT OLD.rate_package_id OR NEW.model_id IS NOT OLD.model_id
    OR NEW.model_version IS NOT OLD.model_version OR NEW.package_version IS NOT OLD.package_version
    OR NEW.source_export_id IS NOT OLD.source_export_id
    OR NEW.publication_receipt_sha256 IS NOT OLD.publication_receipt_sha256
    OR NEW.publication_receipt_json IS NOT OLD.publication_receipt_json
)
BEGIN
    SELECT RAISE(ABORT, 'a package referenced by a monitoring baseline retains its source identity');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_RATE_PACKAGE_BASELINE_IDENTITY_DELETE
BEFORE DELETE ON PRICING_RATE_PACKAGE
WHEN EXISTS (SELECT 1 FROM MODEL_MONITORING_BASELINE WHERE rate_package_id=OLD.rate_package_id)
BEGIN
    SELECT RAISE(ABORT, 'a package referenced by a monitoring baseline retains its source identity');
END;

CREATE TABLE IF NOT EXISTS pricing.MODEL_FIT_CONTRACT (
/*
Purpose: Record the model structure and fitted settings frozen for a monitoring baseline.
One row: One contract for an exact published baseline model run.
Use: Includes levels, groupings, knots, smoothing settings, and comparison grids. A later deployed model starts a new baseline contract.
*/
    fit_contract_id TEXT NOT NULL PRIMARY KEY,
    baseline_model_run_id TEXT NOT NULL UNIQUE,
    model_id INTEGER NOT NULL,
    rate_package_id INTEGER NOT NULL,
    contract_schema_version INTEGER NOT NULL CHECK (contract_schema_version >= 1),
    contract_sha256 TEXT NOT NULL
        CHECK (
            length(contract_sha256) = 64
            AND contract_sha256 = lower(contract_sha256)
            AND contract_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    structure_sha256 TEXT NOT NULL
        CHECK (
            length(structure_sha256) = 64
            AND structure_sha256 = lower(structure_sha256)
            AND structure_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    contract_json TEXT NOT NULL CHECK (json_valid(contract_json)),
    superglm_version TEXT NOT NULL,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    FOREIGN KEY (baseline_model_run_id) REFERENCES MODEL_RUN(model_run_id),
    FOREIGN KEY (model_id) REFERENCES PRICING_MODEL(model_id),
    FOREIGN KEY (rate_package_id) REFERENCES PRICING_RATE_PACKAGE(rate_package_id)
);

CREATE TABLE IF NOT EXISTS pricing.MODEL_MONITOR_RUN (
/*
Purpose: Record a controlled scoring or refitting observation against a deployed baseline.
One row: One deployment, dataset snapshot, component, and monitoring variant.
Use: Writers insert child evidence before sealing the observation in the same transaction. Sealed evidence is immutable. Historical rows are closed without certifying their contents.
*/
    monitor_run_id TEXT NOT NULL PRIMARY KEY,
    fit_contract_id TEXT NOT NULL,
    baseline_deployment_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    rate_package_id INTEGER NOT NULL,
    manifest_id TEXT NOT NULL,
    component_role TEXT NOT NULL
        CHECK (component_role IN ('FREQUENCY', 'SEVERITY', 'OTHER')),
    variant_code TEXT NOT NULL,
    run_signature_sha256 TEXT NOT NULL UNIQUE
        CHECK (
            length(run_signature_sha256) = 64
            AND run_signature_sha256 = lower(run_signature_sha256)
            AND run_signature_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    run_status TEXT NOT NULL CHECK (run_status IN ('SUCCESS', 'FAILED')),
    invariant_status TEXT NOT NULL
        CHECK (invariant_status IN ('VERIFIED', 'LEGACY_UNVERIFIED')),
    invariant_evidence_sha256 TEXT,
    invariant_evidence_json TEXT,
    model_frame_sha256 TEXT NOT NULL
        CHECK (
            length(model_frame_sha256) = 64
            AND model_frame_sha256 = lower(model_frame_sha256)
            AND model_frame_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    fit_configuration_json TEXT NOT NULL CHECK (json_valid(fit_configuration_json)),
    result_evidence_sha256 TEXT NOT NULL
        CHECK (
            length(result_evidence_sha256) = 64
            AND result_evidence_sha256 = lower(result_evidence_sha256)
            AND result_evidence_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    started_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    -- Writers open a run, insert its children, and seal it in one transaction.
    -- Existing observations stay closed without certifying their historical evidence.
    evidence_sealed INTEGER NOT NULL DEFAULT 1 CHECK (evidence_sealed IN (0, 1)),
    CHECK (completed_ts >= started_ts),
    CHECK (
        (
            invariant_status = 'VERIFIED'
            AND invariant_evidence_sha256 IS NOT NULL
            AND length(invariant_evidence_sha256) = 64
            AND invariant_evidence_sha256 = lower(invariant_evidence_sha256)
            AND invariant_evidence_sha256 NOT GLOB '*[^0-9a-f]*'
            AND invariant_evidence_json IS NOT NULL
            AND json_valid(invariant_evidence_json)
        )
        OR (
            invariant_status = 'LEGACY_UNVERIFIED'
            AND invariant_evidence_sha256 IS NULL
            AND invariant_evidence_json IS NULL
        )
    ),
    UNIQUE (baseline_deployment_id, manifest_id, component_role, variant_code),
    FOREIGN KEY (fit_contract_id) REFERENCES MODEL_FIT_CONTRACT(fit_contract_id),
    FOREIGN KEY (baseline_deployment_id)
        REFERENCES PRICING_MODEL_DEPLOYMENT(deployment_id),
    FOREIGN KEY (model_id) REFERENCES PRICING_MODEL(model_id),
    FOREIGN KEY (rate_package_id) REFERENCES PRICING_RATE_PACKAGE(rate_package_id),
    FOREIGN KEY (manifest_id) REFERENCES DATASET_MANIFEST(manifest_id),
    FOREIGN KEY (variant_code) REFERENCES MODEL_MONITOR_VARIANT(variant_code)
);

CREATE TABLE IF NOT EXISTS pricing.MODEL_MONITOR_TERM (
/*
Purpose: Record the model effects observed during a monitoring run.
One row: One term within one monitoring observation, with its kind, order, and structural evidence.
Use: Use with the baseline contract to interpret which structure was held fixed.
*/
    monitor_run_id TEXT NOT NULL,
    term_name TEXT NOT NULL,
    term_kind TEXT NOT NULL,
    sequence_no INTEGER NOT NULL CHECK (sequence_no >= 1),
    term_structure_sha256 TEXT NOT NULL
        CHECK (
            length(term_structure_sha256) = 64
            AND term_structure_sha256 = lower(term_structure_sha256)
            AND term_structure_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    term_metadata_json TEXT NOT NULL CHECK (json_valid(term_metadata_json)),
    PRIMARY KEY (monitor_run_id, term_name),
    UNIQUE (monitor_run_id, sequence_no),
    FOREIGN KEY (monitor_run_id) REFERENCES MODEL_MONITOR_RUN(monitor_run_id)
);

CREATE TABLE IF NOT EXISTS pricing.MODEL_MONITOR_LAMBDA (
/*
Purpose: Record smoothing penalties used in a monitoring observation.
One row: One smoothing component within a monitoring run.
Use: lambda_mode states whether its value came from the baseline, remained fixed, or was estimated again.
*/
    monitor_run_id TEXT NOT NULL,
    component_name TEXT NOT NULL,
    term_name TEXT,
    lambda_value REAL NOT NULL CHECK (lambda_value >= 0),
    lambda_mode TEXT NOT NULL CHECK (lambda_mode IN ('BASELINE', 'FIXED', 'ESTIMATED')),
    PRIMARY KEY (monitor_run_id, component_name),
    FOREIGN KEY (monitor_run_id) REFERENCES MODEL_MONITOR_RUN(monitor_run_id)
);

CREATE TABLE IF NOT EXISTS pricing.MODEL_MONITOR_RELATIVITY (
/*
Purpose: Record monitoring multipliers at comparable feature values.
One row: One categorical level or numeric grid point for a term within a monitoring run.
Use: The baseline defines the comparison points. These are diagnostic values, not a tariff available for deployment.
*/
    monitor_run_id TEXT NOT NULL,
    term_name TEXT NOT NULL,
    term_kind TEXT NOT NULL,
    point_key TEXT NOT NULL,
    point_label TEXT,
    point_numeric REAL,
    relativity REAL NOT NULL CHECK (relativity > 0),
    log_relativity REAL NOT NULL,
    is_reference INTEGER NOT NULL CHECK (is_reference IN (0, 1)),
    PRIMARY KEY (monitor_run_id, term_name, point_key),
    CHECK (
        (point_label IS NULL AND point_numeric IS NOT NULL)
        OR (point_label IS NOT NULL AND point_numeric IS NULL)
    ),
    FOREIGN KEY (monitor_run_id) REFERENCES MODEL_MONITOR_RUN(monitor_run_id)
);

CREATE TABLE IF NOT EXISTS pricing.MODEL_MONITOR_METRIC (
/*
Purpose: Store fit and score measurements for monitoring observations.
One row: One named metric within one monitoring run.
Use: Use the metric name to identify its weighting and interpretation. These measurements are separate from candidate validation results.
*/
    monitor_run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    PRIMARY KEY (monitor_run_id, metric_name),
    FOREIGN KEY (monitor_run_id) REFERENCES MODEL_MONITOR_RUN(monitor_run_id)
);

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_FIT_CONTRACT_LINEAGE_INSERT
BEFORE INSERT ON MODEL_FIT_CONTRACT
WHEN NOT EXISTS (
    SELECT 1
    FROM MODEL_RUN AS baseline_run
    JOIN PRICING_RATE_PACKAGE AS package
      ON package.rate_package_id = NEW.rate_package_id
    WHERE baseline_run.model_run_id = NEW.baseline_model_run_id
      AND baseline_run.model_id = NEW.model_id
      AND baseline_run.rate_package_id = NEW.rate_package_id
      AND baseline_run.run_status = 'SUCCESS'
      AND package.model_id = NEW.model_id
      AND package.package_status = 'PUBLISHED'
)
BEGIN
    SELECT RAISE(
        ABORT,
        'fit contract must identify one successful published baseline run'
    );
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_FIT_CONTRACT_IMMUTABLE_UPDATE
BEFORE UPDATE ON MODEL_FIT_CONTRACT
BEGIN
    SELECT RAISE(ABORT, 'model fit contracts are immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_FIT_CONTRACT_IMMUTABLE_DELETE
BEFORE DELETE ON MODEL_FIT_CONTRACT
BEGIN
    SELECT RAISE(ABORT, 'model fit contracts are immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RUN_MONITORING_LINEAGE_UPDATE
BEFORE UPDATE ON MODEL_RUN
WHEN EXISTS (
    SELECT 1 FROM MODEL_FIT_CONTRACT
    WHERE baseline_model_run_id = OLD.model_run_id
)
AND (
    NEW.model_run_id IS NOT OLD.model_run_id
    OR NEW.model_id IS NOT OLD.model_id
    OR NEW.rate_package_id IS NOT OLD.rate_package_id
    OR NEW.run_status IS NOT OLD.run_status
)
BEGIN
    SELECT RAISE(ABORT, 'a baseline run referenced by a fit contract retains its lineage identity');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RUN_MONITORING_LINEAGE_DELETE
BEFORE DELETE ON MODEL_RUN
WHEN EXISTS (
    SELECT 1 FROM MODEL_FIT_CONTRACT
    WHERE baseline_model_run_id = OLD.model_run_id
)
BEGIN
    SELECT RAISE(ABORT, 'a baseline run referenced by a fit contract retains its lineage identity');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_RUN_LINEAGE_INSERT
BEFORE INSERT ON MODEL_MONITOR_RUN
WHEN NOT EXISTS (
    SELECT 1
    FROM MODEL_FIT_CONTRACT AS contract
    JOIN MODEL_RUN AS baseline_run
      ON baseline_run.model_run_id = contract.baseline_model_run_id
    JOIN PRICING_MODEL_DEPLOYMENT AS deployment
      ON deployment.deployment_id = NEW.baseline_deployment_id
    WHERE contract.fit_contract_id = NEW.fit_contract_id
      AND contract.model_id = NEW.model_id
      AND contract.rate_package_id = NEW.rate_package_id
      AND baseline_run.model_id = NEW.model_id
      AND baseline_run.rate_package_id = NEW.rate_package_id
      AND deployment.model_id = NEW.model_id
      AND deployment.rate_package_id = NEW.rate_package_id
)
BEGIN
    SELECT RAISE(
        ABORT,
        'monitoring contract, run, and deployment must identify one model package'
    );
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_RUN_LINEAGE_UPDATE
BEFORE UPDATE OF fit_contract_id, baseline_deployment_id, model_id, rate_package_id
ON MODEL_MONITOR_RUN
WHEN NOT EXISTS (
    SELECT 1
    FROM MODEL_FIT_CONTRACT AS contract
    JOIN MODEL_RUN AS baseline_run
      ON baseline_run.model_run_id = contract.baseline_model_run_id
    JOIN PRICING_MODEL_DEPLOYMENT AS deployment
      ON deployment.deployment_id = NEW.baseline_deployment_id
    WHERE contract.fit_contract_id = NEW.fit_contract_id
      AND contract.model_id = NEW.model_id
      AND contract.rate_package_id = NEW.rate_package_id
      AND baseline_run.model_id = NEW.model_id
      AND baseline_run.rate_package_id = NEW.rate_package_id
      AND deployment.model_id = NEW.model_id
      AND deployment.rate_package_id = NEW.rate_package_id
)
BEGIN
    SELECT RAISE(
        ABORT,
        'monitoring contract, run, and deployment must identify one model package'
    );
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_DEPLOYMENT_MONITORING_LINEAGE_GUARD_UPDATE
BEFORE UPDATE OF deployment_slot, model_id, rate_package_id, effective_from_ts
ON PRICING_MODEL_DEPLOYMENT
WHEN EXISTS (
    SELECT 1
    FROM MODEL_MONITOR_RUN AS monitor_run
    WHERE monitor_run.baseline_deployment_id = OLD.deployment_id
)
AND (
    NEW.deployment_slot IS NOT OLD.deployment_slot
    OR NEW.model_id IS NOT OLD.model_id
    OR NEW.rate_package_id IS NOT OLD.rate_package_id
    OR NEW.effective_from_ts IS NOT OLD.effective_from_ts
)
BEGIN
    SELECT RAISE(
        ABORT,
        'deployment referenced by monitoring evidence has immutable lineage'
    );
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_DEPLOYMENT_MONITORING_LINEAGE_GUARD_DELETE
BEFORE DELETE ON PRICING_MODEL_DEPLOYMENT
WHEN EXISTS (
    SELECT 1
    FROM MODEL_MONITOR_RUN AS monitor_run
    WHERE monitor_run.baseline_deployment_id = OLD.deployment_id
)
BEGIN
    SELECT RAISE(
        ABORT,
        'deployment referenced by monitoring evidence has immutable lineage'
    );
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_DATASET_MANIFEST_MONITORING_LINEAGE_GUARD_UPDATE
BEFORE UPDATE ON DATASET_MANIFEST
WHEN EXISTS (
    SELECT 1
    FROM MODEL_MONITOR_RUN AS monitor_run
    WHERE monitor_run.manifest_id = OLD.manifest_id
)
BEGIN
    SELECT RAISE(
        ABORT,
        'dataset manifest referenced by monitoring evidence is immutable'
    );
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_DATASET_MANIFEST_MONITORING_LINEAGE_GUARD_DELETE
BEFORE DELETE ON DATASET_MANIFEST
WHEN EXISTS (
    SELECT 1
    FROM MODEL_MONITOR_RUN AS monitor_run
    WHERE monitor_run.manifest_id = OLD.manifest_id
)
BEGIN
    SELECT RAISE(
        ABORT,
        'dataset manifest referenced by monitoring evidence is immutable'
    );
END;

DROP TRIGGER IF EXISTS pricing.TR_MODEL_MONITOR_RUN_IMMUTABLE_UPDATE;
CREATE TRIGGER pricing.TR_MODEL_MONITOR_RUN_IMMUTABLE_UPDATE
BEFORE UPDATE ON MODEL_MONITOR_RUN
WHEN OLD.evidence_sealed != 0 OR NEW.evidence_sealed != 1
    OR NEW.monitor_run_id IS NOT OLD.monitor_run_id
    OR NEW.fit_contract_id IS NOT OLD.fit_contract_id
    OR NEW.baseline_deployment_id IS NOT OLD.baseline_deployment_id
    OR NEW.model_id IS NOT OLD.model_id
    OR NEW.rate_package_id IS NOT OLD.rate_package_id
    OR NEW.manifest_id IS NOT OLD.manifest_id
    OR NEW.component_role IS NOT OLD.component_role
    OR NEW.variant_code IS NOT OLD.variant_code
    OR NEW.run_signature_sha256 IS NOT OLD.run_signature_sha256
    OR NEW.run_status IS NOT OLD.run_status
    OR NEW.invariant_status IS NOT OLD.invariant_status
    OR NEW.invariant_evidence_sha256 IS NOT OLD.invariant_evidence_sha256
    OR NEW.invariant_evidence_json IS NOT OLD.invariant_evidence_json
    OR NEW.model_frame_sha256 IS NOT OLD.model_frame_sha256
    OR NEW.fit_configuration_json IS NOT OLD.fit_configuration_json
    OR NEW.result_evidence_sha256 IS NOT OLD.result_evidence_sha256
    OR NEW.started_ts IS NOT OLD.started_ts
    OR NEW.completed_ts IS NOT OLD.completed_ts
    OR NEW.created_by IS NOT OLD.created_by
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_RUN_IMMUTABLE_DELETE
BEFORE DELETE ON MODEL_MONITOR_RUN
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_TERM_INSERT_GUARD
BEFORE INSERT ON MODEL_MONITOR_TERM
WHEN NOT EXISTS (
    SELECT 1 FROM MODEL_MONITOR_RUN
    WHERE monitor_run_id = NEW.monitor_run_id AND evidence_sealed = 0
)
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is sealed or its parent is missing');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_LAMBDA_INSERT_GUARD
BEFORE INSERT ON MODEL_MONITOR_LAMBDA
WHEN NOT EXISTS (
    SELECT 1 FROM MODEL_MONITOR_RUN
    WHERE monitor_run_id = NEW.monitor_run_id AND evidence_sealed = 0
)
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is sealed or its parent is missing');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_RELATIVITY_INSERT_GUARD
BEFORE INSERT ON MODEL_MONITOR_RELATIVITY
WHEN NOT EXISTS (
    SELECT 1 FROM MODEL_MONITOR_RUN
    WHERE monitor_run_id = NEW.monitor_run_id AND evidence_sealed = 0
)
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is sealed or its parent is missing');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_METRIC_INSERT_GUARD
BEFORE INSERT ON MODEL_MONITOR_METRIC
WHEN NOT EXISTS (
    SELECT 1 FROM MODEL_MONITOR_RUN
    WHERE monitor_run_id = NEW.monitor_run_id AND evidence_sealed = 0
)
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is sealed or its parent is missing');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_TERM_IMMUTABLE_UPDATE
BEFORE UPDATE ON MODEL_MONITOR_TERM
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_TERM_IMMUTABLE_DELETE
BEFORE DELETE ON MODEL_MONITOR_TERM
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_LAMBDA_IMMUTABLE_UPDATE
BEFORE UPDATE ON MODEL_MONITOR_LAMBDA
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_LAMBDA_IMMUTABLE_DELETE
BEFORE DELETE ON MODEL_MONITOR_LAMBDA
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_RELATIVITY_IMMUTABLE_UPDATE
BEFORE UPDATE ON MODEL_MONITOR_RELATIVITY
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_RELATIVITY_IMMUTABLE_DELETE
BEFORE DELETE ON MODEL_MONITOR_RELATIVITY
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_METRIC_IMMUTABLE_UPDATE
BEFORE UPDATE ON MODEL_MONITOR_METRIC
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_MONITOR_METRIC_IMMUTABLE_DELETE
BEFORE DELETE ON MODEL_MONITOR_METRIC
BEGIN
    SELECT RAISE(ABORT, 'monitoring evidence is immutable');
END;

CREATE TABLE IF NOT EXISTS pricing.PRICING_FEATURE (
/*
Purpose: Name an input used by a rating model, such as driver age or region.
One row: One reusable feature name and value type.
Use: A feature is an input variable. MODEL terms describe its main effect or its interaction with other inputs.
*/
    feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name TEXT NOT NULL UNIQUE,
    feature_value_type TEXT NOT NULL,
    is_ordered INTEGER NOT NULL DEFAULT 0,
    active_flag INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_FEATURE_LEVEL_SET (
/*
Purpose: Version the categories or numeric bands available for one rating feature.
One row: One named level set for a feature and model.
Use: Packages refer to a specific set so later changes do not redefine older rating values.
*/
    level_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER,
    feature_id INTEGER NOT NULL,
    level_set_name TEXT NOT NULL,
    level_set_type TEXT NOT NULL,
    binning_strategy TEXT,
    grid_width REAL,
    created_ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (model_id, feature_id, level_set_name)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_FEATURE_LEVEL (
/*
Purpose: Define a category or numeric band within a feature level set.
One row: One level code, label, ordering position, and optional numeric bounds.
Use: For example, a region category or an age band. Missing and other levels are explicit when exported.
*/
    feature_level_id INTEGER PRIMARY KEY AUTOINCREMENT,
    level_set_id INTEGER NOT NULL,
    level_code TEXT NOT NULL,
    level_label TEXT,
    order_index INTEGER,
    lower_bound REAL,
    upper_bound REAL,
    representative_value REAL,
    is_missing INTEGER NOT NULL DEFAULT 0,
    is_other INTEGER NOT NULL DEFAULT 0,
    UNIQUE (level_set_id, level_code)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_TERM (
/*
Purpose: Describe one effect in a rating model.
One row: One main effect, interaction, or exported offset term within a package.
Use: For example, driver age or driver age by region. sequence_no controls display and scoring order.
*/
    term_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate_package_id INTEGER NOT NULL,
    term_name TEXT NOT NULL,
    term_type TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    default_multiplier REAL NOT NULL DEFAULT 1.0,
    default_log_coefficient REAL NOT NULL DEFAULT 0.0,
    term_metadata_json TEXT,
    active_flag INTEGER NOT NULL DEFAULT 1,
    UNIQUE (rate_package_id, term_name)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_TERM_FEATURE (
/*
Purpose: List the input features used by a model effect.
One row: One feature and level-set reference at one position within a term.
Use: An interaction has more than one input. Position determines the order used to build its lookup key.
*/
    term_id INTEGER NOT NULL,
    position_no INTEGER NOT NULL,
    feature_id INTEGER NOT NULL,
    level_set_id INTEGER NOT NULL,
    input_column_name TEXT,
    PRIMARY KEY (term_id, position_no)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_RATE_CELL (
/*
Purpose: Store one rating multiplier for a category, band, or combination of levels.
One row: One lookup entry within a package term, with a multiplier, log coefficient, and supporting weight.
Use: A rate cell is a rating value, not a policy record. A multiplier of 1.12 raises the base rate by 12 percent for that effect. Its levels are in PRICING_RATE_CELL_LEVEL.
*/
    cell_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_id INTEGER NOT NULL,
    cell_key_text TEXT NOT NULL,
    cell_key_digest TEXT NOT NULL,
    multiplier REAL NOT NULL,
    log_coefficient REAL NOT NULL,
    exposure_weight REAL,
    record_count INTEGER,
    is_reference INTEGER NOT NULL DEFAULT 0,
    is_default INTEGER NOT NULL DEFAULT 0,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    UNIQUE (term_id, cell_key_digest)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_RATE_CELL_LEVEL (
/*
Purpose: Identify the feature levels to which a rating multiplier applies.
One row: One feature level at one position in a rating-cell lookup key.
Use: A main-effect cell usually has one level. An interaction cell has one level for each participating feature.
*/
    cell_id INTEGER NOT NULL,
    position_no INTEGER NOT NULL,
    feature_level_id INTEGER NOT NULL,
    PRIMARY KEY (cell_id, position_no)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_COMPILED_RATE_CELL (
/*
Purpose: Store package rating values in the lookup form used by SQL scoring.
One row: One compiled lookup key and multiplier for a package term.
Use: Derived from normalized rating tables during publication. This avoids rebuilding the joins on every score.
*/
    rate_package_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    cell_key_digest TEXT NOT NULL,
    term_name TEXT NOT NULL,
    term_type TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    cell_key_text TEXT NOT NULL,
    multiplier REAL NOT NULL,
    log_coefficient REAL NOT NULL,
    exposure_weight REAL,
    record_count INTEGER,
    is_default INTEGER NOT NULL,
    is_reference INTEGER NOT NULL,
    PRIMARY KEY (rate_package_id, term_id, cell_key_digest)
);

CREATE TABLE IF NOT EXISTS pricing.PRICING_COMPILED_1D_RATE_BAND (
/*
Purpose: Store numeric rating bands in the form used by SQL scoring.
One row: One ordered band within a one-dimensional package term, including bounds and its multiplier.
Use: Derived scoring data. Use V_FINAL_MODEL_RELATIVITY to inspect numeric bands together with categorical and interaction values.
*/
    rate_package_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    feature_level_id INTEGER NOT NULL,
    term_name TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    level_code TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    lower_bound REAL,
    upper_bound REAL,
    representative_value REAL,
    multiplier REAL NOT NULL,
    log_coefficient REAL NOT NULL,
    PRIMARY KEY (rate_package_id, term_id, sort_order, feature_level_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS pricing.UX_PRICING_TERM_PACKAGE_TERM
ON PRICING_TERM(rate_package_id, term_id);

CREATE TABLE IF NOT EXISTS pricing.PRICING_SPLINE_SEGMENT (
/*
Purpose: Preserve exact one-dimensional polynomial spline effects on the log scale.
One row: One ordered segment in one package term, with double precision bounds and coefficients.
Use: Evaluate u=(x-lower_bound)/(upper_bound-lower_bound), then a+u*(b+u*(c+u*d)).
NULL bounds describe constant tails. These rows are not constant interval relativities.
*/
    rate_package_id INTEGER NOT NULL,
    term_id INTEGER NOT NULL,
    segment_order INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    level_label TEXT,
    lower_bound REAL,
    upper_bound REAL,
    upper_inclusive INTEGER NOT NULL CHECK (upper_inclusive IN (0, 1)),
    a REAL NOT NULL,
    b REAL NOT NULL,
    c REAL NOT NULL,
    d REAL NOT NULL,
    exposure_weight REAL,
    PRIMARY KEY (rate_package_id, term_id, segment_order),
    FOREIGN KEY (rate_package_id, term_id) REFERENCES PRICING_TERM(rate_package_id, term_id),
    CHECK (lower_bound IS NULL OR upper_bound IS NULL OR lower_bound < upper_bound),
    CHECK ((lower_bound IS NOT NULL AND upper_bound IS NOT NULL) OR (b = 0 AND c = 0 AND d = 0)),
    CHECK (lower_bound IS NOT NULL OR upper_bound IS NOT NULL)
);

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RECIPE_UPDATE
BEFORE UPDATE ON MODEL_RECIPE BEGIN
    SELECT RAISE(ABORT, 'model recipes are immutable');
END;
CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RECIPE_DELETE
BEFORE DELETE ON MODEL_RECIPE BEGIN
    SELECT RAISE(ABORT, 'model recipes are immutable');
END;
DROP TRIGGER IF EXISTS pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE;
CREATE TRIGGER pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE
BEFORE UPDATE OF model_id, recipe_id, recipe_status, recipe_unavailable_reason ON MODEL_RUN
WHEN (OLD.model_id IS NOT NEW.model_id OR OLD.recipe_id IS NOT NEW.recipe_id OR OLD.recipe_status IS NOT NEW.recipe_status
      OR OLD.recipe_unavailable_reason IS NOT NEW.recipe_unavailable_reason)
BEGIN
    SELECT RAISE(ABORT, 'published run recipe links are immutable');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RUN_RECIPE_INSERT
BEFORE INSERT ON MODEL_RUN
WHEN NEW.recipe_status NOT IN ('CAPTURED', 'LEGACY', 'UNSUPPORTED')
 OR (NEW.recipe_status='CAPTURED' AND (NEW.recipe_id IS NULL OR NEW.recipe_unavailable_reason IS NOT NULL))
 OR (NEW.recipe_status='LEGACY' AND (NEW.recipe_id IS NOT NULL OR NEW.recipe_unavailable_reason IS NOT NULL))
 OR (NEW.recipe_status='UNSUPPORTED' AND (NEW.recipe_id IS NOT NULL OR NEW.recipe_unavailable_reason IS NULL OR trim(NEW.recipe_unavailable_reason)=''))
 OR (NEW.recipe_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM MODEL_RECIPE AS r WHERE r.model_id=NEW.model_id AND r.recipe_id=NEW.recipe_id))
BEGIN
    SELECT RAISE(ABORT, 'invalid same-model recipe link or recipe status');
END;

CREATE TRIGGER IF NOT EXISTS pricing.TR_MODEL_RUN_RECIPE_UPDATE
BEFORE UPDATE ON MODEL_RUN
WHEN NEW.recipe_status NOT IN ('CAPTURED', 'LEGACY', 'UNSUPPORTED')
 OR (NEW.recipe_status='CAPTURED' AND (NEW.recipe_id IS NULL OR NEW.recipe_unavailable_reason IS NOT NULL))
 OR (NEW.recipe_status='LEGACY' AND (NEW.recipe_id IS NOT NULL OR NEW.recipe_unavailable_reason IS NOT NULL))
 OR (NEW.recipe_status='UNSUPPORTED' AND (NEW.recipe_id IS NOT NULL OR NEW.recipe_unavailable_reason IS NULL OR trim(NEW.recipe_unavailable_reason)=''))
 OR (NEW.recipe_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM MODEL_RECIPE AS r WHERE r.model_id=NEW.model_id AND r.recipe_id=NEW.recipe_id))
BEGIN
    SELECT RAISE(ABORT, 'invalid same-model recipe link or recipe status');
END;
