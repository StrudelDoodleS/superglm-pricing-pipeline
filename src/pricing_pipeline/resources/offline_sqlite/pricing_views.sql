DROP VIEW IF EXISTS pricing.V_MODEL_SPLINE_SEGMENT;
DROP VIEW IF EXISTS pricing.V_MODEL_MONITORING_RELATIVITY;
DROP VIEW IF EXISTS pricing.V_MODEL_MONITORING_LAMBDA;
DROP VIEW IF EXISTS pricing.V_MODEL_MONITORING_RUN;
DROP VIEW IF EXISTS pricing.V_CURRENT_DEPLOYED_RELATIVITY;
DROP VIEW IF EXISTS pricing.V_PUBLISHED_MODEL_RELATIVITY;
DROP VIEW IF EXISTS pricing.V_MODEL_CANDIDATE_RELATIVITY;
DROP VIEW IF EXISTS pricing.V_FINAL_MODEL_RELATIVITY;
DROP VIEW IF EXISTS pricing.V_MODEL_RELATIVITY;
DROP VIEW IF EXISTS pricing.V_MODEL_VALIDATION_SUMMARY;
DROP VIEW IF EXISTS pricing.V_MODEL_VALIDATION_SPLIT;
DROP VIEW IF EXISTS pricing.V_MODEL_LINEAGE_REDUNDANCY_CHECK;
-- Upgrade cleanup for short-lived audit views whose duplicate states are
-- already made impossible by filtered unique indexes.
DROP VIEW IF EXISTS pricing.V_DATASET_MANIFEST_REDUNDANCY_CHECK;
DROP VIEW IF EXISTS pricing.V_MODEL_EQUIVALENCE_REDUNDANCY_CHECK;

CREATE VIEW pricing.V_MODEL_RELATIVITY AS
/*
Purpose: Combine numeric bands and other rating entries into one internal representation.
One row: One numeric band or categorical or interaction lookup entry within a model package.
Use: Includes all package statuses and versions. Both branches describe the package model. Analysts should use V_FINAL_MODEL_RELATIVITY for dataset and validation context.
*/
SELECT
    m.model_id,
    m.model_name,
    m.model_label,
    m.target_name,
    m.model_type,
    mr.model_run_id,
    mr.parent_model_run_id,
    mr.run_status,
    rp.rate_package_id,
    rp.parent_rate_package_id,
    rp.model_name AS package_model_name,
    rp.model_version,
    rp.package_version,
    rp.base_rate,
    rp.effective_from_date,
    rp.effective_to_date,
    rp.package_status,
    b.term_id,
    t.sequence_no AS term_sequence_no,
    b.term_name,
    t.term_type,
    CAST(b.level_code AS TEXT) AS level_value,
    b.sort_order AS level_sort_order,
    b.lower_bound,
    b.upper_bound,
    b.representative_value,
    b.multiplier AS relativity,
    b.log_coefficient,
    crc.exposure_weight,
    crc.record_count,
    crc.is_default,
    crc.is_reference,
    '1D_RATE_BAND' AS relativity_source,
    'PACKAGE_FINAL_MODEL' AS model_fit_scope
FROM PRICING_MODEL AS m
JOIN PRICING_RATE_PACKAGE AS rp
  ON rp.model_id = m.model_id
LEFT JOIN MODEL_RUN AS mr
  ON mr.rate_package_id = rp.rate_package_id
JOIN PRICING_COMPILED_1D_RATE_BAND AS b
  ON b.rate_package_id = rp.rate_package_id
JOIN PRICING_TERM AS t
  ON t.term_id = b.term_id
JOIN PRICING_RATE_CELL_LEVEL AS rcl
  ON rcl.feature_level_id = b.feature_level_id
 AND rcl.position_no = 1
JOIN PRICING_RATE_CELL AS rc
  ON rc.cell_id = rcl.cell_id
 AND rc.term_id = b.term_id
 AND rc.is_deleted = 0
JOIN PRICING_COMPILED_RATE_CELL AS crc
  ON crc.rate_package_id = b.rate_package_id
 AND crc.term_id = b.term_id
 AND crc.cell_key_digest = rc.cell_key_digest

UNION ALL

SELECT
    m.model_id,
    m.model_name,
    m.model_label,
    m.target_name,
    m.model_type,
    mr.model_run_id,
    mr.parent_model_run_id,
    mr.run_status,
    rp.rate_package_id,
    rp.parent_rate_package_id,
    rp.model_name AS package_model_name,
    rp.model_version,
    rp.package_version,
    rp.base_rate,
    rp.effective_from_date,
    rp.effective_to_date,
    rp.package_status,
    c.term_id,
    c.sequence_no AS term_sequence_no,
    c.term_name,
    c.term_type,
    CASE
        WHEN substr(c.cell_key_text, 1, length(c.term_name) + 1) = c.term_name || '='
        THEN substr(c.cell_key_text, length(c.term_name) + 2)
        ELSE c.cell_key_text
    END AS level_value,
    NULL AS level_sort_order,
    NULL AS lower_bound,
    NULL AS upper_bound,
    NULL AS representative_value,
    c.multiplier AS relativity,
    c.log_coefficient,
    c.exposure_weight,
    c.record_count,
    c.is_default,
    c.is_reference,
    'RATE_CELL' AS relativity_source,
    'PACKAGE_FINAL_MODEL' AS model_fit_scope
FROM PRICING_MODEL AS m
JOIN PRICING_RATE_PACKAGE AS rp
  ON rp.model_id = m.model_id
LEFT JOIN MODEL_RUN AS mr
  ON mr.rate_package_id = rp.rate_package_id
JOIN PRICING_COMPILED_RATE_CELL AS c
  ON c.rate_package_id = rp.rate_package_id
WHERE c.term_type <> 'SPLINE_PPOLY_1D'
AND NOT EXISTS (
    SELECT 1
    FROM PRICING_COMPILED_1D_RATE_BAND AS b
    WHERE b.rate_package_id = c.rate_package_id
      AND b.term_id = c.term_id
);

CREATE VIEW pricing.V_FINAL_MODEL_RELATIVITY AS
/*
Purpose: Inspect every exported model effect with model dates and dataset lineage.
One row: One lookup entry, numeric coefficient, per-unit factor, or spline segment.
Use: Read representation before evaluating. SPLINE rows have NULL relativity and log_coefficient;
use their bounds, upper_inclusive and a/b/c/d. Final means the package model, not latest or deployed.
SPLINE coefficients define the exact fitted log-effect polynomial:
u=(x-lower_bound)/(upper_bound-lower_bound), log effect=a+u*(b+u*(c+u*d)).
Relativity is EXP(log effect). NULL bounds are constant tails with log effect a.
*/
WITH rating_entries AS (
    SELECT * FROM V_MODEL_RELATIVITY
    UNION ALL
    SELECT
        m.model_id, m.model_name, m.model_label, m.target_name, m.model_type,
        mr.model_run_id, mr.parent_model_run_id, mr.run_status,
        rp.rate_package_id, rp.parent_rate_package_id,
        rp.model_name AS package_model_name, rp.model_version, rp.package_version,
        rp.base_rate, rp.effective_from_date, rp.effective_to_date, rp.package_status,
        s.term_id, t.sequence_no AS term_sequence_no, t.term_name, t.term_type,
        CAST(s.level_label AS TEXT) AS level_value,
        s.segment_order AS level_sort_order, s.lower_bound, s.upper_bound,
        CAST(NULL AS REAL) AS representative_value,
        CAST(NULL AS REAL) AS relativity, CAST(NULL AS REAL) AS log_coefficient,
        s.exposure_weight, CAST(NULL AS INT) AS record_count,
        CAST(0 AS INT) AS is_default, CAST(0 AS INT) AS is_reference,
        'SPLINE_SEGMENT' AS relativity_source, 'PACKAGE_FINAL_MODEL' AS model_fit_scope
    FROM PRICING_SPLINE_SEGMENT AS s
    JOIN PRICING_TERM AS t
      ON t.term_id = s.term_id AND t.rate_package_id = s.rate_package_id
    JOIN PRICING_RATE_PACKAGE AS rp ON rp.rate_package_id = s.rate_package_id
    JOIN PRICING_MODEL AS m ON m.model_id = rp.model_id
    LEFT JOIN MODEL_RUN AS mr ON mr.rate_package_id = rp.rate_package_id
)
SELECT
    relativity.model_id,
    relativity.model_name,
    relativity.model_label,
    relativity.target_name,
    relativity.model_type,
    model_run.model_kind,
    recipe.recipe_revision, recipe.recipe_sha256, COALESCE(model_run.recipe_status, 'LEGACY') AS recipe_status,
    model_run.model_equivalence_sha256,
    relativity.model_run_id,
    relativity.parent_model_run_id,
    relativity.run_status,
    model_run.export_id,
    relativity.rate_package_id,
    relativity.parent_rate_package_id,
    relativity.package_model_name,
    relativity.model_version,
    relativity.package_version,
    relativity.base_rate,
    relativity.effective_from_date,
    relativity.effective_to_date,
    relativity.package_status,
    manifest.manifest_id,
    manifest.manifest_signature_sha256,
    manifest.dataset_name,
    manifest.source_system,
    manifest.data_as_of_date,
    manifest.data_as_of_column,
    manifest.row_count AS dataset_row_count,
    manifest.pk_columns_json,
    manifest.target_column AS dataset_target_column,
    manifest.weight_column,
    manifest.exposure_column,
    manifest.offset_column,
    manifest.offset_source_column,
    manifest.offset_label,
    manifest.export_weight_column,
    manifest.model_frame_sha256,
    manifest.frame_hash_metadata_json,
    manifest.created_ts AS manifest_created_ts,
    manifest.created_by AS manifest_created_by,
    model_run.split_set_id AS validation_split_set_id,
    relativity.term_id,
    relativity.term_sequence_no,
    relativity.term_name,
    relativity.term_type,
    relativity.level_value,
    relativity.level_sort_order,
    relativity.lower_bound,
    relativity.upper_bound,
    relativity.representative_value,
    relativity.relativity,
    relativity.log_coefficient,
    relativity.exposure_weight,
    relativity.record_count,
    relativity.is_default,
    relativity.is_reference,
    relativity.relativity_source,
    relativity.model_fit_scope,
    CASE
        WHEN relativity.term_type = 'SPLINE_PPOLY_1D' THEN 'SPLINE'
        WHEN relativity.term_type = 'NUMERIC_MAIN' THEN 'NUMERIC'
        WHEN relativity.term_type = 'OFFSET_FACTOR'
             AND json_extract(term.term_metadata_json, '$.rating_representation') = 'PER_UNIT_FACTOR'
        THEN 'PER_UNIT_FACTOR'
        ELSE 'LOOKUP'
    END AS representation,
    CASE WHEN relativity.term_type = 'CATEGORICAL_INTERACTION' THEN NULL
         ELSE COALESCE(segment.feature_name, relativity.term_name)
    END AS feature_name,
    segment.upper_inclusive, segment.a, segment.b, segment.c, segment.d,
    model_run.completed_ts AS model_completed_ts,
    package.package_metadata_json,
    term.term_metadata_json,
    json_extract(package.package_metadata_json, '$.input_preparation.transforms') AS transforms_json
FROM rating_entries AS relativity
LEFT JOIN PRICING_SPLINE_SEGMENT AS segment
  ON segment.rate_package_id = relativity.rate_package_id
 AND segment.term_id = relativity.term_id
 AND segment.segment_order = relativity.level_sort_order
 AND relativity.term_type = 'SPLINE_PPOLY_1D'
LEFT JOIN PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id = relativity.rate_package_id
LEFT JOIN PRICING_TERM AS term
  ON term.term_id = relativity.term_id AND term.rate_package_id = relativity.rate_package_id
LEFT JOIN MODEL_RUN AS model_run
  ON model_run.model_run_id = relativity.model_run_id
LEFT JOIN MODEL_RECIPE AS recipe ON recipe.model_id=model_run.model_id AND recipe.recipe_id=model_run.recipe_id
LEFT JOIN DATASET_MANIFEST AS manifest
  ON manifest.manifest_id = model_run.manifest_id;

CREATE VIEW pricing.V_MODEL_CANDIDATE_RELATIVITY AS
/*
Purpose: Compare rating multipliers across published model packages.
One row: One rating entry within a PUBLISHED package, with dataset and validation context.
Use: Includes historical published packages. Publication does not mean deployment. Use V_CURRENT_DEPLOYED_RELATIVITY for the selected package in each slot.
*/
SELECT *
FROM V_FINAL_MODEL_RELATIVITY
WHERE package_status = 'PUBLISHED';

-- Compatibility alias retained for existing notebook and reporting queries.
CREATE VIEW pricing.V_PUBLISHED_MODEL_RELATIVITY AS
/*
Purpose: Provide the compatibility name for published candidate rating multipliers.
One row: The same rating entries and columns as V_MODEL_CANDIDATE_RELATIVITY.
Use: New queries should use V_MODEL_CANDIDATE_RELATIVITY. This name remains for existing SQL consumers.
*/
SELECT *
FROM V_MODEL_CANDIDATE_RELATIVITY;

CREATE VIEW pricing.V_CURRENT_DEPLOYED_RELATIVITY AS
/*
Purpose: Inspect rating multipliers for the current deployment of each model and slot.
One row: One rating entry per open deployment of a PUBLISHED package.
Use: Includes deployment details and dataset context. The same package can appear in several slots; include deployment_slot when comparing results.
*/
SELECT
    deployment.deployment_id,
    deployment.deployment_slot,
    deployment.effective_from_ts AS deployment_effective_from_ts,
    deployment.effective_to_ts AS deployment_effective_to_ts,
    deployment.deployed_by,
    deployment.deployment_note,
    deployment.created_ts AS deployment_created_ts,
    relativity.*
FROM PRICING_MODEL_DEPLOYMENT AS deployment
JOIN V_FINAL_MODEL_RELATIVITY AS relativity
  ON relativity.model_id = deployment.model_id
 AND relativity.rate_package_id = deployment.rate_package_id
WHERE deployment.effective_to_ts IS NULL
  AND relativity.package_status = 'PUBLISHED';

CREATE VIEW pricing.V_MODEL_MONITORING_RUN AS
/*
Purpose: Compare monitoring observations with their deployed baseline and dated dataset.
One row: One sealed monitoring observation for a component and variant.
Use: Includes historical baseline deployments, status, and stored evidence digests. These observations are not candidate packages.
*/
SELECT
    monitor_run.monitor_run_id,
    monitor_run.variant_code,
    variant.variant_label,
    variant.refit_coefficients,
    variant.reestimate_lambdas,
    variant.reposition_data_driven_knots,
    monitor_run.component_role,
    monitor_run.run_status,
    monitor_run.invariant_status,
    monitor_run.invariant_evidence_sha256,
    monitor_run.invariant_evidence_json,
    monitor_run.model_frame_sha256 AS observed_model_frame_sha256,
    monitor_run.fit_configuration_json,
    monitor_run.result_evidence_sha256,
    monitor_run.started_ts,
    monitor_run.completed_ts,
    monitor_run.created_by,
    monitor_run.run_signature_sha256,
    contract.fit_contract_id,
    contract.baseline_model_run_id,
    recipe.recipe_revision AS baseline_recipe_revision, recipe.recipe_sha256 AS baseline_recipe_sha256, baseline_run.recipe_status AS baseline_recipe_status,
    contract.contract_sha256,
    contract.structure_sha256,
    contract.superglm_version,
    monitor_run.baseline_deployment_id,
    deployment.deployment_slot AS baseline_deployment_slot,
    monitor_run.model_id,
    model.model_name,
    model.model_label,
    model.target_name,
    model.model_type,
    monitor_run.rate_package_id,
    package.model_version AS baseline_model_version,
    package.package_version AS baseline_package_version,
    monitor_run.manifest_id,
    manifest.manifest_signature_sha256,
    manifest.dataset_name,
    manifest.source_system,
    manifest.data_as_of_date,
    manifest.data_as_of_column,
    manifest.row_count AS dataset_row_count,
    manifest.model_frame_sha256
FROM MODEL_MONITOR_RUN AS monitor_run
JOIN MODEL_MONITOR_VARIANT AS variant
  ON variant.variant_code = monitor_run.variant_code
JOIN MODEL_FIT_CONTRACT AS contract
  ON contract.fit_contract_id = monitor_run.fit_contract_id
LEFT JOIN MODEL_RUN AS baseline_run ON baseline_run.model_run_id=contract.baseline_model_run_id
LEFT JOIN MODEL_RECIPE AS recipe ON recipe.model_id=baseline_run.model_id AND recipe.recipe_id=baseline_run.recipe_id
JOIN PRICING_MODEL_DEPLOYMENT AS deployment
  ON deployment.deployment_id = monitor_run.baseline_deployment_id
JOIN PRICING_MODEL AS model
  ON model.model_id = monitor_run.model_id
JOIN PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id = monitor_run.rate_package_id
JOIN DATASET_MANIFEST AS manifest
  ON manifest.manifest_id = monitor_run.manifest_id
WHERE monitor_run.evidence_sealed = 1;

CREATE VIEW pricing.V_MODEL_MONITORING_RELATIVITY AS
/*
Purpose: Compare monitoring multipliers on the baseline feature grid.
One row: One term comparison point within a monitoring observation.
Use: Use baseline deployment, component, variant, and data-as-at to compare like-for-like observations. These multipliers are diagnostic, not deployable.
*/
SELECT
    monitoring_run.*,
    relativity.term_name,
    term.sequence_no AS term_sequence_no,
    relativity.term_kind,
    term.term_structure_sha256,
    term.term_metadata_json,
    relativity.point_key,
    relativity.point_label,
    relativity.point_numeric,
    relativity.relativity,
    relativity.log_relativity,
    relativity.is_reference
FROM V_MODEL_MONITORING_RUN AS monitoring_run
JOIN MODEL_MONITOR_RELATIVITY AS relativity
  ON relativity.monitor_run_id = monitoring_run.monitor_run_id
JOIN MODEL_MONITOR_TERM AS term
  ON term.monitor_run_id = relativity.monitor_run_id
 AND term.term_name = relativity.term_name;

CREATE VIEW pricing.V_MODEL_MONITORING_LAMBDA AS
/*
Purpose: Compare smoothing penalties across monitoring observations.
One row: One smoothing component within a monitoring observation.
Use: lambda_mode distinguishes baseline, fixed, and estimated values. Compare within the same baseline contract.
*/
SELECT
    monitoring_run.*,
    lambda.component_name,
    lambda.term_name,
    lambda.lambda_value,
    lambda.lambda_mode
FROM V_MODEL_MONITORING_RUN AS monitoring_run
JOIN MODEL_MONITOR_LAMBDA AS lambda
  ON lambda.monitor_run_id = monitoring_run.monitor_run_id;

CREATE VIEW pricing.V_MODEL_VALIDATION_SPLIT AS
/*
Purpose: Compare held-out validation performance fold by fold.
One row: One fold with recorded metrics for a successful model run and its validation split set.
Use: Includes deviance, negative log-likelihood, and Gini where recorded. Runs without fold metrics are absent.
*/
SELECT
    mr.model_run_id,
    mr.parent_model_run_id,
    m.model_id,
    m.model_name,
    m.model_label,
    m.target_name,
    m.model_type,
    mr.model_kind,
    mr.model_equivalence_sha256,
    mr.model_version,
    mr.export_id,
    mr.run_status,
    rp.rate_package_id,
    rp.parent_rate_package_id,
    rp.package_version,
    rp.package_status,
    dm.manifest_id,
    dm.dataset_name,
    dm.source_system,
    dm.data_as_of_date,
    dm.row_count AS dataset_row_count,
    ss.split_set_id,
    ss.split_mode,
    ss.splitter_class,
    ss.splitter_params_json,
    ss.fold_count AS configured_fold_count,
    fold.fold_no AS validation_split_no,
    fold.n_train,
    fold.n_test,
    MAX(CASE WHEN fm.metric_name = 'deviance' THEN fm.metric_value END) AS deviance,
    MAX(CASE WHEN fm.metric_name = 'nll' THEN fm.metric_value END) AS nll,
    MAX(CASE WHEN fm.metric_name = 'gini' THEN fm.metric_value END) AS gini
-- SQLite cannot persist a pricing view that references the separately attached
-- mlops database, and this view must remain usable when pricing.sqlite is opened
-- directly. Local publication separately writes and verifies the equivalent
-- training/validation MODEL_RUN_SPLIT_SET link. SQL Server uses that normalized
-- role-filtered link in V035.
FROM MODEL_RUN AS mr
JOIN PRICING_MODEL AS m
  ON m.model_id = mr.model_id
JOIN PRICING_RATE_PACKAGE AS rp
  ON rp.rate_package_id = mr.rate_package_id
JOIN DATASET_MANIFEST AS dm
  ON dm.manifest_id = mr.manifest_id
JOIN CV_SPLIT_SET AS ss
  ON ss.manifest_id = mr.manifest_id
 AND ss.split_set_id = mr.split_set_id
JOIN CV_FOLD AS fold
  ON fold.split_set_id = ss.split_set_id
JOIN CV_FOLD_METRIC AS fm
  ON fm.model_run_id = mr.model_run_id
 AND fm.split_set_id = fold.split_set_id
 AND fm.fold_no = fold.fold_no
WHERE mr.run_status = 'SUCCESS'
GROUP BY
    mr.model_run_id,
    mr.parent_model_run_id,
    m.model_id,
    m.model_name,
    m.model_label,
    m.target_name,
    m.model_type,
    mr.model_kind,
    mr.model_equivalence_sha256,
    mr.model_version,
    mr.export_id,
    mr.run_status,
    rp.rate_package_id,
    rp.parent_rate_package_id,
    rp.package_version,
    rp.package_status,
    dm.manifest_id,
    dm.dataset_name,
    dm.source_system,
    dm.data_as_of_date,
    dm.row_count,
    ss.split_set_id,
    ss.split_mode,
    ss.splitter_class,
    ss.splitter_params_json,
    ss.fold_count,
    fold.fold_no,
    fold.n_train,
    fold.n_test;

CREATE VIEW pricing.V_MODEL_VALIDATION_SUMMARY AS
/*
Purpose: Compare validation performance across recorded model runs.
One row: One model run represented in the fold-validation view, with run-level and fold summaries.
Use: Pooled and full-fit metrics live in mlops.MODEL_RUN_METRIC. SQLite cannot join attached databases in a persistent view, so those columns are NULL here. Query mlops directly for their values. Runs without fold evidence are absent.
*/
WITH recipe_validation AS (
    SELECT validation.*, recipe.recipe_revision, recipe.recipe_sha256, model_run.recipe_status
    FROM V_MODEL_VALIDATION_SPLIT AS validation
    JOIN MODEL_RUN AS model_run ON model_run.model_run_id=validation.model_run_id
    LEFT JOIN MODEL_RECIPE AS recipe ON recipe.model_id=model_run.model_id AND recipe.recipe_id=model_run.recipe_id
)
SELECT
    model_run_id,
    parent_model_run_id,
    model_id,
    model_name,
    model_label,
    target_name,
    model_type,
    model_kind,
    model_equivalence_sha256,
    model_version,
    export_id,
    run_status,
    rate_package_id,
    parent_rate_package_id,
    package_version,
    package_status,
    manifest_id,
    dataset_name,
    source_system,
    data_as_of_date,
    dataset_row_count,
    split_set_id,
    split_mode,
    splitter_class,
    splitter_params_json,
    configured_fold_count,
    MAX(recipe_revision) AS recipe_revision, MAX(recipe_sha256) AS recipe_sha256, MAX(recipe_status) AS recipe_status,
    COUNT(*) AS recorded_split_count,
    SUM(n_test) AS total_validation_rows,
    AVG(deviance) AS mean_deviance,
    sqrt(MAX(AVG(deviance * deviance) - AVG(deviance) * AVG(deviance), 0.0))
        AS std_deviance,
    -- Pooled scores live in the separately attached mlops database. SQLite
    -- cannot expose them from a persistent pricing.sqlite view without copying
    -- audit data, so local callers inspect candidate.metrics or mlops directly.
    CAST(NULL AS REAL) AS pooled_deviance,
    AVG(nll) AS mean_nll,
    sqrt(MAX(AVG(nll * nll) - AVG(nll) * AVG(nll), 0.0)) AS std_nll,
    CAST(NULL AS REAL) AS pooled_nll,
    AVG(gini) AS mean_gini,
    sqrt(MAX(AVG(gini * gini) - AVG(gini) * AVG(gini), 0.0)) AS std_gini,
    CAST(NULL AS REAL) AS pooled_gini,
    CAST(SUM(n_test) AS REAL) / dataset_row_count AS oof_coverage,
    -- Full-fit metrics also live in mlops; query that table in local mode.
    CAST(NULL AS REAL) AS fit_converged,
    CAST(NULL AS REAL) AS fit_n_iter,
    CAST(NULL AS REAL) AS fit_deviance,
    CAST(NULL AS REAL) AS fit_effective_df,
    CAST(NULL AS REAL) AS fit_phi,
    CAST(NULL AS REAL) AS fit_log_likelihood,
    CAST(NULL AS REAL) AS fit_null_log_likelihood,
    CAST(NULL AS REAL) AS fit_null_deviance,
    CAST(NULL AS REAL) AS fit_explained_deviance,
    CAST(NULL AS REAL) AS fit_pearson_chi2,
    CAST(NULL AS REAL) AS fit_n_obs,
    CAST(NULL AS REAL) AS fit_likelihood_size,
    CAST(NULL AS REAL) AS fit_reml_enabled,
    CAST(NULL AS REAL) AS fit_reml_converged,
    CAST(NULL AS REAL) AS fit_reml_n_iter
FROM recipe_validation
GROUP BY
    model_run_id,
    parent_model_run_id,
    model_id,
    model_name,
    model_label,
    target_name,
    model_type,
    model_kind,
    model_equivalence_sha256,
    model_version,
    export_id,
    run_status,
    rate_package_id,
    parent_rate_package_id,
    package_version,
    package_status,
    manifest_id,
    dataset_name,
    source_system,
    data_as_of_date,
    dataset_row_count,
    split_set_id,
    split_mode,
    splitter_class,
    splitter_params_json,
    configured_fold_count;

CREATE VIEW pricing.V_MODEL_LINEAGE_REDUNDANCY_CHECK AS
/*
Purpose: Find disagreements in stored model-run dataset and validation links.
One row: One model run joined to a package, with a diagnostic status.
Use: Filter redundancy_status <> OK to investigate missing, extra, or conflicting links. OK covers these link checks only; it does not verify artifacts or every integrity rule.
*/
SELECT
    model_run.model_id,
    model_run.model_run_id,
    package.rate_package_id,
    package.manifest_id AS package_manifest_id,
    model_run.manifest_id AS run_manifest_id,
    CAST(NULL AS TEXT) AS linked_training_manifest_id,
    CAST(NULL AS INTEGER) AS training_manifest_link_count,
    package.split_set_id AS package_split_set_id,
    model_run.split_set_id AS run_split_set_id,
    CAST(NULL AS TEXT) AS linked_validation_split_set_id,
    CAST(NULL AS INTEGER) AS validation_split_link_count,
    CASE
        WHEN package.manifest_id IS NOT NULL
         AND package.manifest_id <> model_run.manifest_id
        THEN 'PACKAGE_RUN_MANIFEST_MISMATCH'
        WHEN package.split_set_id IS NOT NULL
         AND package.split_set_id <> model_run.split_set_id
        THEN 'PACKAGE_RUN_SPLIT_MISMATCH'
        ELSE 'OK'
    END AS redundancy_status
FROM MODEL_RUN AS model_run
JOIN PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id = model_run.rate_package_id;

CREATE VIEW pricing.V_MODEL_SPLINE_SEGMENT AS
/*
Purpose: Expose exact spline segments with model, dataset, and preparation metadata.
One row: One polynomial segment of a package term across all package statuses.
Use: Prepare feature_name with transforms_json, then evaluate the normalized polynomial.
NULL bounds are constant tails. a is a log effect at the segment origin, not a band relativity.
*/
SELECT
    m.model_id, m.model_name, m.model_label, m.target_name, m.model_type,
    mr.model_run_id, mr.parent_model_run_id, mr.run_status, mr.model_kind,
    mr.completed_ts AS model_completed_ts,
    mr.model_equivalence_sha256, mr.export_id, mr.manifest_id, mr.split_set_id,
    dm.dataset_name, dm.source_system, dm.data_as_of_date, dm.row_count AS dataset_row_count,
    rp.rate_package_id, rp.parent_rate_package_id, rp.model_version, rp.package_version,
    rp.base_rate, rp.package_status, rp.effective_from_date, rp.effective_to_date,
    rp.package_metadata_json,
    json_extract(rp.package_metadata_json, '$.input_preparation.transforms') AS transforms_json,
    t.term_id, t.term_name, t.term_type, t.sequence_no AS term_sequence_no, t.term_metadata_json,
    s.segment_order, s.feature_name, s.level_label,
    s.lower_bound, s.upper_bound, s.upper_inclusive, s.a, s.b, s.c, s.d, s.exposure_weight
FROM PRICING_SPLINE_SEGMENT AS s
JOIN PRICING_TERM AS t ON t.term_id = s.term_id AND t.rate_package_id = s.rate_package_id
JOIN PRICING_RATE_PACKAGE AS rp ON rp.rate_package_id = s.rate_package_id
JOIN PRICING_MODEL AS m ON m.model_id = rp.model_id
LEFT JOIN MODEL_RUN AS mr ON mr.rate_package_id = rp.rate_package_id
LEFT JOIN DATASET_MANIFEST AS dm ON dm.manifest_id = mr.manifest_id;
