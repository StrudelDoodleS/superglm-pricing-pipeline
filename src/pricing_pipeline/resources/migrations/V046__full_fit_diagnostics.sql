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

EXEC sys.sp_updateextendedproperty
    @name = N'MS_Description',
    @value = N'Purpose: Compare validation performance and full-training fit diagnostics across model runs.
One row: One model run represented in the fold-validation view, with run-level and fold summaries.
Use: Pooled metrics describe held-out predictions. fit_* columns describe the full training fit. Missing diagnostics are NULL. Convergence flags use 1 for true and 0 for false. Runs without fold evidence are absent.',
    @level0type = N'SCHEMA', @level0name = N'pricing',
    @level1type = N'VIEW', @level1name = N'V_MODEL_VALIDATION_SUMMARY';
GO

EXEC sys.sp_updateextendedproperty
    @name = N'MS_Description',
    @value = N'Purpose: Store run-level model performance and fit diagnostics.
One row: One named metric and scope for a model run.
Use: Scope cv contains held-out scores. Scope full_fit contains full-training diagnostics named fit_*. Missing diagnostics have no row. Fold metrics live in CV_FOLD_METRIC.',
    @level0type = N'SCHEMA', @level0name = N'mlops',
    @level1type = N'TABLE', @level1name = N'MODEL_RUN_METRIC';
GO
