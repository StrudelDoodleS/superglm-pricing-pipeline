-- One analyst-facing view for all exported model effects.

CREATE OR ALTER VIEW pricing.V_FINAL_MODEL_RELATIVITY
AS
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
    SELECT * FROM pricing.V_MODEL_RELATIVITY
    UNION ALL
    SELECT
        m.model_id, m.model_name, m.model_label, m.target_name, m.model_type,
        mr.model_run_id, mr.parent_model_run_id, mr.run_status,
        rp.rate_package_id, rp.parent_rate_package_id,
        rp.model_name AS package_model_name, rp.model_version, rp.package_version,
        rp.base_rate, rp.effective_from_date, rp.effective_to_date, rp.package_status,
        s.term_id, t.sequence_no AS term_sequence_no, t.term_name, t.term_type,
        CAST(s.level_label AS NVARCHAR(900)) AS level_value,
        s.segment_order AS level_sort_order, s.lower_bound, s.upper_bound,
        CAST(NULL AS FLOAT) AS representative_value,
        CAST(NULL AS DECIMAL(19,10)) AS relativity,
        CAST(NULL AS DECIMAL(19,12)) AS log_coefficient,
        s.exposure_weight, CAST(NULL AS INT) AS record_count,
        CAST(0 AS INT) AS is_default, CAST(0 AS INT) AS is_reference,
        'SPLINE_SEGMENT' AS relativity_source, 'PACKAGE_FINAL_MODEL' AS model_fit_scope
    FROM pricing.PRICING_SPLINE_SEGMENT AS s
    JOIN pricing.PRICING_TERM AS t
      ON t.term_id = s.term_id AND t.rate_package_id = s.rate_package_id
    JOIN pricing.PRICING_RATE_PACKAGE AS rp ON rp.rate_package_id = s.rate_package_id
    JOIN pricing.PRICING_MODEL AS m ON m.model_id = rp.model_id
    LEFT JOIN pricing.MODEL_RUN AS mr ON mr.rate_package_id = rp.rate_package_id
),
validation_split_links AS (
    SELECT
        model_run_id,
        COUNT_BIG(*) AS validation_split_link_count,
        CASE
            WHEN COUNT_BIG(*) = 1 THEN MAX(manifest_id)
            ELSE NULL
        END AS validation_manifest_id,
        CASE
            WHEN COUNT_BIG(*) = 1 THEN MAX(split_set_id)
            ELSE NULL
        END AS validation_split_set_id
    FROM mlops.MODEL_RUN_SPLIT_SET
    WHERE dataset_role = 'training'
      AND split_role = 'validation'
    GROUP BY model_run_id
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
    validation_split.validation_manifest_id
        AS validation_split_manifest_id,
    validation_split.validation_split_set_id,
    COALESCE(validation_split.validation_split_link_count, 0)
        AS validation_split_link_count,
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
             AND JSON_VALUE(term.term_metadata_json, '$.rating_representation') = 'PER_UNIT_FACTOR'
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
    JSON_QUERY(package.package_metadata_json, '$.input_preparation.transforms') AS transforms_json
FROM rating_entries AS relativity
LEFT JOIN pricing.PRICING_SPLINE_SEGMENT AS segment
  ON segment.rate_package_id = relativity.rate_package_id
 AND segment.term_id = relativity.term_id
 AND segment.segment_order = relativity.level_sort_order
 AND relativity.term_type = 'SPLINE_PPOLY_1D'
LEFT JOIN pricing.PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id = relativity.rate_package_id
LEFT JOIN pricing.PRICING_TERM AS term
  ON term.term_id = relativity.term_id AND term.rate_package_id = relativity.rate_package_id
LEFT JOIN pricing.MODEL_RUN AS model_run
  ON model_run.model_run_id = relativity.model_run_id
LEFT JOIN pricing.MODEL_RECIPE AS recipe ON recipe.model_id=model_run.model_id AND recipe.recipe_id=model_run.recipe_id
LEFT JOIN mlops.MODEL_RUN_DATASET AS run_dataset
  ON run_dataset.model_run_id = model_run.model_run_id
 AND run_dataset.dataset_role = 'training'
 AND run_dataset.manifest_id = model_run.manifest_id
LEFT JOIN pricing.DATASET_MANIFEST AS manifest
  ON manifest.manifest_id = COALESCE(run_dataset.manifest_id, model_run.manifest_id)
LEFT JOIN validation_split_links AS validation_split
  ON validation_split.model_run_id = model_run.model_run_id;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_VALIDATION_SUMMARY
AS
/*
Purpose: Compare validation performance and full-training fit diagnostics across model runs.
One row: One model run represented in the fold-validation view, with run-level and fold summaries.
Use: Pooled metrics come from held-out predictions across folds. They are not generally the average of fold metrics. fit_* columns describe the full training fit, not held-out performance. Missing diagnostics are NULL. Convergence flags use 1 for true and 0 for false. Runs without fold evidence are absent.
*/
WITH run_metrics AS (
    SELECT
        metric.model_run_id,
        MAX(
            CASE WHEN metric.metric_name = 'cv_mean_deviance'
                THEN metric.metric_value END
        ) AS mean_deviance,
        MAX(
            CASE WHEN metric.metric_name = 'cv_std_deviance'
                THEN metric.metric_value END
        ) AS std_deviance,
        MAX(
            CASE WHEN metric.metric_name = 'cv_pooled_deviance'
                THEN metric.metric_value END
        ) AS pooled_deviance,
        MAX(
            CASE WHEN metric.metric_name = 'cv_mean_nll'
                THEN metric.metric_value END
        ) AS mean_nll,
        MAX(
            CASE WHEN metric.metric_name = 'cv_std_nll'
                THEN metric.metric_value END
        ) AS std_nll,
        MAX(
            CASE WHEN metric.metric_name = 'cv_pooled_nll'
                THEN metric.metric_value END
        ) AS pooled_nll,
        MAX(
            CASE WHEN metric.metric_name = 'cv_mean_gini'
                THEN metric.metric_value END
        ) AS mean_gini,
        MAX(
            CASE WHEN metric.metric_name = 'cv_std_gini'
                THEN metric.metric_value END
        ) AS std_gini,
        MAX(
            CASE WHEN metric.metric_name = 'cv_pooled_gini'
                THEN metric.metric_value END
        ) AS pooled_gini,
        MAX(
            CASE WHEN metric.metric_name = 'cv_oof_coverage'
                THEN metric.metric_value END
        ) AS oof_coverage,
        MAX(CASE WHEN metric.metric_name = 'fit_converged'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_converged,
        MAX(CASE WHEN metric.metric_name = 'fit_n_iter'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_n_iter,
        MAX(CASE WHEN metric.metric_name = 'fit_deviance'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_deviance,
        MAX(CASE WHEN metric.metric_name = 'fit_effective_df'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_effective_df,
        MAX(CASE WHEN metric.metric_name = 'fit_phi'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_phi,
        MAX(CASE WHEN metric.metric_name = 'fit_log_likelihood'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_log_likelihood,
        MAX(CASE WHEN metric.metric_name = 'fit_null_log_likelihood'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_null_log_likelihood,
        MAX(CASE WHEN metric.metric_name = 'fit_null_deviance'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_null_deviance,
        MAX(CASE WHEN metric.metric_name = 'fit_explained_deviance'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_explained_deviance,
        MAX(CASE WHEN metric.metric_name = 'fit_pearson_chi2'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_pearson_chi2,
        MAX(CASE WHEN metric.metric_name = 'fit_n_obs'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_n_obs,
        MAX(CASE WHEN metric.metric_name = 'fit_likelihood_size'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_likelihood_size,
        MAX(CASE WHEN metric.metric_name = 'fit_reml_enabled'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_reml_enabled,
        MAX(CASE WHEN metric.metric_name = 'fit_reml_converged'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_reml_converged,
        MAX(CASE WHEN metric.metric_name = 'fit_reml_n_iter'
            AND metric.metric_scope = 'full_fit' THEN metric.metric_value END) AS fit_reml_n_iter
    FROM mlops.MODEL_RUN_METRIC AS metric
    GROUP BY metric.model_run_id
)
SELECT
    validation.model_run_id,
    validation.parent_model_run_id,
    validation.model_id,
    validation.model_name,
    validation.model_label,
    validation.target_name,
    validation.model_type,
    validation.model_version,
    validation.export_id,
    validation.run_status,
    validation.rate_package_id,
    validation.parent_rate_package_id,
    validation.package_version,
    validation.package_status,
    validation.manifest_id,
    validation.dataset_name,
    validation.source_system,
    validation.data_as_of_date,
    validation.dataset_row_count,
    validation.split_set_id,
    validation.split_mode,
    validation.splitter_class,
    validation.splitter_params_json,
    validation.configured_fold_count,
    MAX(recipe.recipe_revision) AS recipe_revision, MAX(recipe.recipe_sha256) AS recipe_sha256, MAX(model_run.recipe_status) AS recipe_status,
    COUNT_BIG(*) AS recorded_split_count,
    SUM(validation.n_test) AS total_validation_rows,
    MAX(metrics.mean_deviance) AS mean_deviance,
    MAX(metrics.std_deviance) AS std_deviance,
    MAX(metrics.pooled_deviance) AS pooled_deviance,
    MAX(metrics.mean_nll) AS mean_nll,
    MAX(metrics.std_nll) AS std_nll,
    MAX(metrics.pooled_nll) AS pooled_nll,
    MAX(metrics.mean_gini) AS mean_gini,
    MAX(metrics.std_gini) AS std_gini,
    MAX(metrics.pooled_gini) AS pooled_gini,
    MAX(metrics.oof_coverage) AS oof_coverage,
    MAX(metrics.fit_converged) AS fit_converged,
    MAX(metrics.fit_n_iter) AS fit_n_iter,
    MAX(metrics.fit_deviance) AS fit_deviance,
    MAX(metrics.fit_effective_df) AS fit_effective_df,
    MAX(metrics.fit_phi) AS fit_phi,
    MAX(metrics.fit_log_likelihood) AS fit_log_likelihood,
    MAX(metrics.fit_null_log_likelihood) AS fit_null_log_likelihood,
    MAX(metrics.fit_null_deviance) AS fit_null_deviance,
    MAX(metrics.fit_explained_deviance) AS fit_explained_deviance,
    MAX(metrics.fit_pearson_chi2) AS fit_pearson_chi2,
    MAX(metrics.fit_n_obs) AS fit_n_obs,
    MAX(metrics.fit_likelihood_size) AS fit_likelihood_size,
    MAX(metrics.fit_reml_enabled) AS fit_reml_enabled,
    MAX(metrics.fit_reml_converged) AS fit_reml_converged,
    MAX(metrics.fit_reml_n_iter) AS fit_reml_n_iter
FROM pricing.V_MODEL_VALIDATION_SPLIT AS validation
JOIN pricing.MODEL_RUN AS model_run ON model_run.model_run_id=validation.model_run_id
LEFT JOIN pricing.MODEL_RECIPE AS recipe ON recipe.model_id=model_run.model_id AND recipe.recipe_id=model_run.recipe_id
LEFT JOIN run_metrics AS metrics
  ON metrics.model_run_id = validation.model_run_id
GROUP BY
    validation.model_run_id,
    validation.parent_model_run_id,
    validation.model_id,
    validation.model_name,
    validation.model_label,
    validation.target_name,
    validation.model_type,
    validation.model_version,
    validation.export_id,
    validation.run_status,
    validation.rate_package_id,
    validation.parent_rate_package_id,
    validation.package_version,
    validation.package_status,
    validation.manifest_id,
    validation.dataset_name,
    validation.source_system,
    validation.data_as_of_date,
    validation.dataset_row_count,
    validation.split_set_id,
    validation.split_mode,
    validation.splitter_class,
    validation.splitter_params_json,
    validation.configured_fold_count;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_MONITORING_RUN AS
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
FROM mlops.MODEL_MONITOR_RUN AS monitor_run
JOIN mlops.MODEL_MONITOR_VARIANT AS variant
  ON variant.variant_code = monitor_run.variant_code
JOIN mlops.MODEL_FIT_CONTRACT AS contract
  ON contract.fit_contract_id = monitor_run.fit_contract_id
LEFT JOIN pricing.MODEL_RUN AS baseline_run ON baseline_run.model_run_id=contract.baseline_model_run_id
LEFT JOIN pricing.MODEL_RECIPE AS recipe ON recipe.model_id=baseline_run.model_id AND recipe.recipe_id=baseline_run.recipe_id
JOIN pricing.PRICING_MODEL_DEPLOYMENT AS deployment
  ON deployment.deployment_id = monitor_run.baseline_deployment_id
JOIN pricing.PRICING_MODEL AS model
  ON model.model_id = monitor_run.model_id
JOIN pricing.PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id = monitor_run.rate_package_id
JOIN pricing.DATASET_MANIFEST AS manifest
  ON manifest.manifest_id = monitor_run.manifest_id
WHERE monitor_run.evidence_sealed = 1;
GO

EXEC sys.sp_refreshview N'pricing.V_MODEL_CANDIDATE_RELATIVITY';
EXEC sys.sp_refreshview N'pricing.V_PUBLISHED_MODEL_RELATIVITY';
EXEC sys.sp_refreshview N'pricing.V_CURRENT_DEPLOYED_RELATIVITY';
EXEC sys.sp_refreshview N'pricing.V_MODEL_MONITORING_RELATIVITY';
EXEC sys.sp_refreshview N'pricing.V_MODEL_MONITORING_LAMBDA';
GO
