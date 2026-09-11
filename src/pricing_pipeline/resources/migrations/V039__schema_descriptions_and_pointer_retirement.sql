-- Retire duplicate writable deployment state after checking that history preserves it.
-- Stop old application writers before applying this migration and deploy the matching code.
IF OBJECT_ID('pricing.PRICING_PACKAGE_POINTER', 'U') IS NOT NULL
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pricing.PRICING_PACKAGE_POINTER AS pointer WITH (TABLOCKX, HOLDLOCK)
        WHERE NOT EXISTS (
            SELECT 1
            FROM pricing.PRICING_MODEL_DEPLOYMENT AS deployment WITH (HOLDLOCK)
            WHERE deployment.model_id = pointer.model_id
              AND deployment.deployment_slot = pointer.pointer_name
              AND deployment.rate_package_id = pointer.rate_package_id
              AND deployment.effective_to_ts IS NULL
        )
    )
    BEGIN;
        THROW 51040, 'Cannot retire package pointer: reconcile unmatched pointers with current deployment history first.', 1;
    END;

    IF EXISTS (
        SELECT 1 FROM sys.sql_expression_dependencies
        WHERE referenced_id = OBJECT_ID('pricing.PRICING_PACKAGE_POINTER')
          AND referencing_id <> OBJECT_ID('pricing.PRICING_PACKAGE_POINTER')
    )
    BEGIN;
        THROW 51041, 'Cannot retire package pointer: migrate SQL objects that still reference it first.', 1;
    END;

    DROP TABLE pricing.PRICING_PACKAGE_POINTER;
END;
GO

CREATE OR ALTER VIEW pricing.V_ACTIVE_MODEL AS
/*
Purpose: List business models whose registry status is ACTIVE.
One row: One active model identity.
Use: ACTIVE is a registry status. It does not mean the model has a published or deployed package.
*/
SELECT
    model_id,
    model_name,
    model_label,
    target_name,
    model_type,
    model_status,
    created_ts,
    created_by,
    retired_ts
FROM pricing.PRICING_MODEL
WHERE model_status = 'ACTIVE';
GO

CREATE OR ALTER VIEW pricing.V_CURRENT_RATE_PACKAGE AS
/*
Purpose: Resolve the current package for each model and deployment slot.
One row: One open deployment, with model and package details.
Use: Current means effective_to_ts IS NULL. PREDICT_CURRENT_RATE uses this view to select the scoring package.
*/
SELECT
    d.deployment_id,
    d.deployment_slot,
    d.effective_from_ts,
    d.model_id,
    m.model_name,
    m.target_name,
    m.model_type,
    rp.rate_package_id,
    rp.parent_rate_package_id,
    rp.model_name AS package_model_name,
    rp.model_version,
    rp.package_version,
    rp.base_rate,
    rp.effective_from_date,
    rp.effective_to_date,
    rp.package_status,
    rp.created_ts,
    rp.created_by
FROM pricing.PRICING_MODEL_DEPLOYMENT d
JOIN pricing.PRICING_MODEL m
  ON m.model_id = d.model_id
JOIN pricing.PRICING_RATE_PACKAGE rp
  ON rp.rate_package_id = d.rate_package_id
WHERE d.effective_to_ts IS NULL;
GO

CREATE OR ALTER VIEW pricing.V_CURRENT_RATE_CELL AS
/*
Purpose: Inspect compiled rating lookup values for current deployments.
One row: One compiled rating entry per open deployment and term.
Use: A package deployed in two slots appears twice. For analyst comparisons, use V_CURRENT_DEPLOYED_RELATIVITY.
*/
SELECT
    cur.model_id,
    cur.model_name,
    cur.deployment_slot,
    cur.rate_package_id,
    cur.package_version,
    c.term_id,
    c.cell_key_digest,
    c.term_name,
    c.term_type,
    c.sequence_no,
    c.cell_key_text,
    c.multiplier,
    c.log_coefficient,
    c.exposure_weight,
    c.record_count,
    c.is_default,
    c.is_reference
FROM pricing.V_CURRENT_RATE_PACKAGE cur
JOIN pricing.PRICING_COMPILED_RATE_CELL c
  ON c.rate_package_id = cur.rate_package_id;
GO

CREATE OR ALTER VIEW pricing.V_CURRENT_1D_RATE_BAND AS
/*
Purpose: Inspect numeric rating bands for current deployments.
One row: One numeric band per open deployment and term.
Use: Contains numeric bands only. V_CURRENT_DEPLOYED_RELATIVITY also includes categorical and interaction rating values.
*/
SELECT
    cur.model_id,
    cur.model_name,
    cur.deployment_slot,
    cur.rate_package_id,
    cur.package_version,
    b.term_id,
    b.feature_level_id,
    b.term_name,
    b.feature_name,
    b.level_code,
    b.sort_order,
    b.lower_bound,
    b.upper_bound,
    b.representative_value,
    b.multiplier,
    b.log_coefficient
FROM pricing.V_CURRENT_RATE_PACKAGE cur
JOIN pricing.PRICING_COMPILED_1D_RATE_BAND b
  ON b.rate_package_id = cur.rate_package_id;
GO

CREATE OR ALTER VIEW pricing.V_CURRENT_DATASET_CV_FOLD
AS
/*
Purpose: Inspect folds for the most recently registered dataset and split set.
One row: One fold in the newest split set of the newest manifest for each dataset name.
Use: Newest means created_ts, not data-as-at or deployment. train_folds_json lists other fold labels, not exact training-row membership; use the verified split artifact for that.
*/
WITH current_manifest AS (
    SELECT
        dm.manifest_id,
        dm.dataset_name,
        dm.source_system,
        dm.data_as_of_date,
        dm.data_as_of_column,
        dm.row_count AS dataset_row_count,
        dm.pk_columns_json,
        dm.target_column,
        dm.weight_column,
        dm.offset_column,
        dm.offset_source_column,
        dm.offset_label,
        dm.export_weight_column,
        dm.model_frame_sha256,
        dm.frame_hash_metadata_json,
        dm.created_ts AS manifest_created_ts,
        dm.created_by AS manifest_created_by,
        ROW_NUMBER() OVER (
            PARTITION BY dataset_name
            ORDER BY dm.created_ts DESC, dm.manifest_id DESC
        ) AS manifest_rank
    FROM pricing.DATASET_MANIFEST dm
),
current_split_set AS (
    SELECT
        ss.split_set_id,
        ss.manifest_id,
        ss.split_mode,
        ss.splitter_class,
        ss.splitter_params_json,
        ss.row_order_sha256,
        ss.row_count AS split_row_count,
        ss.fold_count,
        ss.groups_column,
        ss.stratify_column,
        ss.artifact_uri,
        ss.artifact_sha256,
        ss.runtime_metadata_json,
        ss.created_ts AS split_created_ts,
        ss.created_by AS split_created_by,
        ROW_NUMBER() OVER (
            PARTITION BY manifest_id
            ORDER BY ss.created_ts DESC, ss.split_set_id DESC
        ) AS split_rank
    FROM pricing.CV_SPLIT_SET ss
)
SELECT
    cm.dataset_name,
    cm.manifest_id,
    cm.source_system,
    cm.data_as_of_date,
    cm.data_as_of_column,
    cm.dataset_row_count,
    cm.pk_columns_json,
    cm.target_column,
    cm.weight_column,
    cm.offset_column,
    cm.offset_source_column,
    cm.offset_label,
    cm.export_weight_column,
    cm.model_frame_sha256,
    cm.frame_hash_metadata_json,
    cm.manifest_created_ts,
    cm.manifest_created_by,
    css.split_set_id,
    css.split_mode,
    css.splitter_class,
    css.splitter_params_json,
    css.row_order_sha256,
    css.split_row_count,
    css.fold_count,
    css.groups_column,
    css.stratify_column,
    css.artifact_uri,
    css.artifact_sha256,
    css.runtime_metadata_json,
    css.split_created_ts,
    css.split_created_by,
    fold.fold_no AS split_no,
    CONCAT('[', COALESCE(train_folds.train_folds_csv, ''), ']') AS train_folds_json,
    fold.fold_no AS test_fold_no,
    fold.n_train,
    fold.n_test
FROM current_manifest cm
JOIN current_split_set css
  ON css.manifest_id = cm.manifest_id
 AND css.split_rank = 1
JOIN pricing.CV_FOLD fold
  ON fold.split_set_id = css.split_set_id
OUTER APPLY (
    SELECT
        STRING_AGG(CONVERT(VARCHAR(12), train_fold.fold_no), ',')
            WITHIN GROUP (ORDER BY train_fold.fold_no) AS train_folds_csv
    FROM pricing.CV_FOLD train_fold
    WHERE train_fold.split_set_id = fold.split_set_id
      AND train_fold.fold_no <> fold.fold_no
) train_folds
WHERE cm.manifest_rank = 1;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_RELATIVITY
AS
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
    CAST(b.level_code AS NVARCHAR(900)) AS level_value,
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
FROM pricing.PRICING_MODEL AS m
JOIN pricing.PRICING_RATE_PACKAGE AS rp
  ON rp.model_id = m.model_id
LEFT JOIN pricing.MODEL_RUN AS mr
  ON mr.rate_package_id = rp.rate_package_id
JOIN pricing.PRICING_COMPILED_1D_RATE_BAND AS b
  ON b.rate_package_id = rp.rate_package_id
JOIN pricing.PRICING_TERM AS t
  ON t.term_id = b.term_id
JOIN pricing.PRICING_RATE_CELL_LEVEL AS rcl
  ON rcl.feature_level_id = b.feature_level_id
 AND rcl.position_no = 1
JOIN pricing.PRICING_RATE_CELL AS rc
  ON rc.cell_id = rcl.cell_id
 AND rc.term_id = b.term_id
 AND rc.is_deleted = 0
JOIN pricing.PRICING_COMPILED_RATE_CELL AS crc
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
        WHEN LEFT(c.cell_key_text, LEN(c.term_name) + 1) = CONCAT(c.term_name, '=')
        THEN SUBSTRING(c.cell_key_text, LEN(c.term_name) + 2, 900)
        ELSE c.cell_key_text
    END AS level_value,
    CAST(NULL AS INT) AS level_sort_order,
    CAST(NULL AS FLOAT) AS lower_bound,
    CAST(NULL AS FLOAT) AS upper_bound,
    CAST(NULL AS FLOAT) AS representative_value,
    c.multiplier AS relativity,
    c.log_coefficient,
    c.exposure_weight,
    c.record_count,
    c.is_default,
    c.is_reference,
    'RATE_CELL' AS relativity_source,
    'PACKAGE_FINAL_MODEL' AS model_fit_scope
FROM pricing.PRICING_MODEL AS m
JOIN pricing.PRICING_RATE_PACKAGE AS rp
  ON rp.model_id = m.model_id
LEFT JOIN pricing.MODEL_RUN AS mr
  ON mr.rate_package_id = rp.rate_package_id
JOIN pricing.PRICING_COMPILED_RATE_CELL AS c
  ON c.rate_package_id = rp.rate_package_id
WHERE NOT EXISTS (
    SELECT 1
    FROM pricing.PRICING_COMPILED_1D_RATE_BAND AS b
    WHERE b.rate_package_id = c.rate_package_id
      AND b.term_id = c.term_id
);
GO

CREATE OR ALTER VIEW pricing.V_PUBLISHED_MODEL_RELATIVITY
AS
/*
Purpose: Provide the compatibility name for published candidate rating multipliers.
One row: The same rating entries and columns as V_MODEL_CANDIDATE_RELATIVITY.
Use: New queries should use V_MODEL_CANDIDATE_RELATIVITY. This name remains for existing SQL consumers.
*/
SELECT *
FROM pricing.V_FINAL_MODEL_RELATIVITY
WHERE package_status = 'PUBLISHED';
GO

CREATE OR ALTER VIEW pricing.V_FINAL_MODEL_RELATIVITY
AS
/*
Purpose: Compare package rating multipliers with their model and dataset context.
One row: One numeric band or categorical or interaction lookup entry, enriched with dataset and validation lineage.
Use: Final describes the exported package model. It does not mean latest, published, approved, or deployed. Includes all statuses; use candidate or deployed views when state matters. relativity is the multiplier applied for this effect.
*/
WITH validation_split_links AS (
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
    relativity.model_fit_scope
FROM pricing.V_MODEL_RELATIVITY AS relativity
LEFT JOIN pricing.MODEL_RUN AS model_run
  ON model_run.model_run_id = relativity.model_run_id
LEFT JOIN mlops.MODEL_RUN_DATASET AS run_dataset
  ON run_dataset.model_run_id = model_run.model_run_id
 AND run_dataset.dataset_role = 'training'
 AND run_dataset.manifest_id = model_run.manifest_id
LEFT JOIN pricing.DATASET_MANIFEST AS manifest
  ON manifest.manifest_id = COALESCE(run_dataset.manifest_id, model_run.manifest_id)
LEFT JOIN validation_split_links AS validation_split
  ON validation_split.model_run_id = model_run.model_run_id;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_VALIDATION_SPLIT
AS
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
FROM pricing.MODEL_RUN AS mr
JOIN pricing.PRICING_MODEL AS m
  ON m.model_id = mr.model_id
JOIN pricing.PRICING_RATE_PACKAGE AS rp
  ON rp.rate_package_id = mr.rate_package_id
JOIN mlops.MODEL_RUN_SPLIT_SET AS run_split
  ON run_split.model_run_id = mr.model_run_id
 AND run_split.dataset_role = 'training'
 AND run_split.split_role = 'validation'
JOIN pricing.DATASET_MANIFEST AS dm
  ON dm.manifest_id = run_split.manifest_id
JOIN pricing.CV_SPLIT_SET AS ss
  ON ss.manifest_id = run_split.manifest_id
 AND ss.split_set_id = run_split.split_set_id
JOIN pricing.CV_FOLD AS fold
  ON fold.split_set_id = ss.split_set_id
JOIN pricing.CV_FOLD_METRIC AS fm
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
GO

CREATE OR ALTER VIEW pricing.V_MODEL_VALIDATION_SUMMARY
AS
/*
Purpose: Compare validation performance across recorded model runs.
One row: One model run represented in the fold-validation view, with run-level and fold summaries.
Use: Pooled metrics come from held-out predictions across folds. They are not generally the average of fold metrics. Runs without fold evidence are absent.
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
        ) AS oof_coverage
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
    MAX(metrics.oof_coverage) AS oof_coverage
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

CREATE OR ALTER VIEW pricing.V_MODEL_CANDIDATE_RELATIVITY
AS
/*
Purpose: Compare rating multipliers across published model packages.
One row: One rating entry within a PUBLISHED package, with dataset and validation context.
Use: Includes historical published packages. Publication does not mean deployment. Use V_CURRENT_DEPLOYED_RELATIVITY for the selected package in each slot.
*/
SELECT *
FROM pricing.V_FINAL_MODEL_RELATIVITY
WHERE package_status = 'PUBLISHED';
GO

CREATE OR ALTER VIEW pricing.V_CURRENT_DEPLOYED_RELATIVITY
AS
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
FROM pricing.PRICING_MODEL_DEPLOYMENT AS deployment
JOIN pricing.V_FINAL_MODEL_RELATIVITY AS relativity
  ON relativity.model_id = deployment.model_id
 AND relativity.rate_package_id = deployment.rate_package_id
WHERE deployment.effective_to_ts IS NULL
  AND relativity.package_status = 'PUBLISHED';
GO

CREATE OR ALTER VIEW pricing.V_MODEL_LINEAGE_REDUNDANCY_CHECK
AS
/*
Purpose: Find disagreements in stored model-run dataset and validation links.
One row: One model run joined to a package, with a diagnostic status.
Use: Filter redundancy_status <> OK to investigate missing, extra, or conflicting links. OK covers these link checks only; it does not verify artifacts or every integrity rule.
*/
WITH dataset_links AS (
    SELECT
        model_run_id,
        SUM(CASE WHEN dataset_role = 'training' THEN 1 ELSE 0 END)
            AS training_manifest_link_count,
        MAX(CASE WHEN dataset_role = 'training' THEN manifest_id END)
            AS linked_training_manifest_id
    FROM mlops.MODEL_RUN_DATASET
    GROUP BY model_run_id
),
split_links AS (
    SELECT
        model_run_id,
        SUM(
            CASE
                WHEN dataset_role = 'training' AND split_role = 'validation'
                THEN 1 ELSE 0
            END
        ) AS validation_split_link_count,
        MAX(
            CASE
                WHEN dataset_role = 'training' AND split_role = 'validation'
                THEN split_set_id
            END
        ) AS linked_validation_split_set_id,
        MAX(
            CASE
                WHEN dataset_role = 'training' AND split_role = 'validation'
                THEN manifest_id
            END
        ) AS linked_validation_manifest_id
    FROM mlops.MODEL_RUN_SPLIT_SET
    GROUP BY model_run_id
)
SELECT
    model_run.model_id,
    model_run.model_run_id,
    package.rate_package_id,
    model_run.manifest_id AS run_manifest_id,
    dataset_links.linked_training_manifest_id,
    dataset_links.training_manifest_link_count,
    split_links.linked_validation_manifest_id,
    split_links.linked_validation_split_set_id,
    split_links.validation_split_link_count,
    CASE
        WHEN model_run.manifest_id IS NULL
         AND COALESCE(dataset_links.training_manifest_link_count, 0) <> 0
        THEN 'UNEXPECTED_TRAINING_MANIFEST_LINK'
        WHEN model_run.manifest_id IS NOT NULL
         AND COALESCE(dataset_links.training_manifest_link_count, 0) <> 1
        THEN 'TRAINING_MANIFEST_LINK_COUNT'
        WHEN dataset_links.linked_training_manifest_id <> model_run.manifest_id
        THEN 'RUN_MANIFEST_LINK_MISMATCH'
        WHEN COALESCE(split_links.validation_split_link_count, 0) > 1
        THEN 'VALIDATION_SPLIT_LINK_COUNT'
        WHEN COALESCE(split_links.validation_split_link_count, 0) = 1
         AND (
                model_run.manifest_id IS NULL
                OR split_links.linked_validation_manifest_id
                    <> model_run.manifest_id
            )
        THEN 'VALIDATION_SPLIT_MANIFEST_MISMATCH'
        ELSE 'OK'
    END AS redundancy_status
FROM pricing.MODEL_RUN AS model_run
JOIN pricing.PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id = model_run.rate_package_id
LEFT JOIN dataset_links
  ON dataset_links.model_run_id = model_run.model_run_id
LEFT JOIN split_links
  ON split_links.model_run_id = model_run.model_run_id;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_MONITORING_RUN
AS
/*
Purpose: Compare monitoring observations with their deployed baseline and dated dataset.
One row: One recorded monitoring observation for a component and variant.
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
JOIN pricing.PRICING_MODEL_DEPLOYMENT AS deployment
  ON deployment.deployment_id = monitor_run.baseline_deployment_id
JOIN pricing.PRICING_MODEL AS model
  ON model.model_id = monitor_run.model_id
JOIN pricing.PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id = monitor_run.rate_package_id
JOIN pricing.DATASET_MANIFEST AS manifest
  ON manifest.manifest_id = monitor_run.manifest_id;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_MONITORING_RELATIVITY
AS
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
FROM pricing.V_MODEL_MONITORING_RUN AS monitoring_run
JOIN mlops.MODEL_MONITOR_RELATIVITY AS relativity
  ON relativity.monitor_run_id = monitoring_run.monitor_run_id
JOIN mlops.MODEL_MONITOR_TERM AS term
  ON term.monitor_run_id = relativity.monitor_run_id
 AND term.term_name = relativity.term_name;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_MONITORING_LAMBDA
AS
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
FROM pricing.V_MODEL_MONITORING_RUN AS monitoring_run
JOIN mlops.MODEL_MONITOR_LAMBDA AS lambda
  ON lambda.monitor_run_id = monitoring_run.monitor_run_id;
GO

-- Object descriptions appear in SQL Server properties and sys.extended_properties.
-- Tables do not store CREATE TABLE source text, so their durable comments live here.
DECLARE @object_descriptions TABLE (
    schema_name SYSNAME NOT NULL,
    object_name SYSNAME NOT NULL,
    object_type VARCHAR(5) NOT NULL,
    description NVARCHAR(3500) NOT NULL
);
INSERT INTO @object_descriptions (schema_name, object_name, object_type, description)
VALUES
    (N'dbo', N'SCHEMA_CONFIGURATION', 'TABLE', N'Purpose: Keep the schema names chosen when this database was initialized.
One row: One configuration key and its fixed schema name.
Use: The migration runner rejects a different schema mapping for an initialized database.'),
    (N'dbo', N'SCHEMA_MIGRATION', 'TABLE', N'Purpose: Record which schema migrations were applied and their checksums.
One row: One migration filename, with application status, actor, time, and any error.
Use: Use the migration runner. Editing an applied migration breaks checksum verification.'),
    (N'mlops', N'MODEL_FIT_CONTRACT', 'TABLE', N'Purpose: Record the model structure and fitted settings frozen for a monitoring baseline.
One row: One contract for an exact published baseline model run.
Use: Includes levels, groupings, knots, smoothing settings, and comparison grids. A later deployed model starts a new baseline contract.'),
    (N'mlops', N'MODEL_MONITOR_LAMBDA', 'TABLE', N'Purpose: Record smoothing penalties used in a monitoring observation.
One row: One smoothing component within a monitoring run.
Use: lambda_mode states whether its value came from the baseline, remained fixed, or was estimated again.'),
    (N'mlops', N'MODEL_MONITOR_METRIC', 'TABLE', N'Purpose: Store fit and score measurements for monitoring observations.
One row: One named metric within one monitoring run.
Use: Use the metric name to identify its weighting and interpretation. These measurements are separate from candidate validation results.'),
    (N'mlops', N'MODEL_MONITOR_RELATIVITY', 'TABLE', N'Purpose: Record monitoring multipliers at comparable feature values.
One row: One categorical level or numeric grid point for a term within a monitoring run.
Use: The baseline defines the comparison points. These are diagnostic values, not a tariff available for deployment.'),
    (N'mlops', N'MODEL_MONITOR_RUN', 'TABLE', N'Purpose: Record a controlled scoring or refitting observation against a deployed baseline.
One row: One deployment, dataset snapshot, component, and monitoring variant.
Use: Records invariant checks and evidence digests. Monitoring observations do not create or deploy rating packages.'),
    (N'mlops', N'MODEL_MONITOR_TERM', 'TABLE', N'Purpose: Record the model effects observed during a monitoring run.
One row: One term within one monitoring observation, with its kind, order, and structural evidence.
Use: Use with the baseline contract to interpret which structure was held fixed.'),
    (N'mlops', N'MODEL_MONITOR_VARIANT', 'TABLE', N'Purpose: Define the four supported monitoring comparisons against a deployed model.
One row: One preset describing whether coefficients, smoothing penalties, and data-driven knots may change.
Use: These presets produce monitoring evidence, not deployable candidate packages.'),
    (N'mlops', N'MODEL_RUN_DATASET', 'TABLE', N'Purpose: Link a recorded model run to datasets by their role.
One row: One model run, dataset role, and manifest reference.
Use: Current builds record the training role. The training link must agree with MODEL_RUN.manifest_id; the redundancy-check view reports disagreement.'),
    (N'mlops', N'MODEL_RUN_METRIC', 'TABLE', N'Purpose: Store run-level model performance measurements.
One row: One named metric and optional scope for a model run.
Use: Includes pooled and summary validation results. Fold-level measurements are stored separately in CV_FOLD_METRIC.'),
    (N'mlops', N'MODEL_RUN_SPLIT_SET', 'TABLE', N'Purpose: Link a model run to the validation split used for a dataset.
One row: One split-set reference and split role for a model run.
Use: This is the SQL Server source of run-to-split lineage. Current builds use training and validation roles.'),
    (N'pricing', N'CV_FOLD', 'TABLE', N'Purpose: Record the size of each validation split.
One row: One fold number within a split set, with training and test row counts.
Use: This table contains counts, not individual row membership. A holdout also has a fold record.'),
    (N'pricing', N'CV_FOLD_METRIC', 'TABLE', N'Purpose: Store predictive performance measured on each held-out fold.
One row: One metric for one model run, split set, and fold.
Use: Compare runs on the same split set. These results differ from full-sample training metrics and pooled validation metrics.'),
    (N'pricing', N'CV_SPLIT_SET', 'TABLE', N'Purpose: Identify how a dataset was split for validation.
One row: One split configuration and ordered-row identity for one manifest.
Use: Exact row membership comes from replaying the recorded configuration or loading its verified split artifact.'),
    (N'pricing', N'DATASET_COLUMN', 'TABLE', N'Purpose: Describe columns in a recorded dataset snapshot.
One row: One column within a dataset manifest, with its role, type, and summary statistics.
Use: Use this to check the model inputs without loading policy records.'),
    (N'pricing', N'DATASET_MANIFEST', 'TABLE', N'Purpose: Identify the exact dataset snapshot used for a model or monitoring observation.
One row: One dataset version, with its data-as-at date, row count, column roles, and content hashes.
Use: Data-as-at describes source completeness. It is separate from the import or fit time. Source records live in the model-frame artifact.'),
    (N'pricing', N'FREMTPL_RAW', 'TABLE', N'Purpose: Hold the public freMTPL motor claim frequency data for demonstrations.
One row: One source policy record, including claim count and exposure in years.
Use: This is demo input. Production model lineage uses DATASET_MANIFEST and the model-frame artifact.'),
    (N'pricing', N'MODEL_RUN', 'TABLE', N'Purpose: Record a model build or an edited revision and its audit evidence.
One row: One recorded run with its model, training manifest, package, parent, status, and artifact hashes.
Use: model_kind distinguishes RAW, ROUTINE_EDIT, EDITOR_EDIT, and MANUAL_EDIT. Publication and deployment are separate steps.'),
    (N'pricing', N'PRICING_COMPILED_1D_RATE_BAND', 'TABLE', N'Purpose: Store numeric rating bands in the form used by SQL scoring.
One row: One ordered band within a one-dimensional package term, including bounds and its multiplier.
Use: Derived scoring data. Use V_FINAL_MODEL_RELATIVITY to inspect numeric bands together with categorical and interaction values.'),
    (N'pricing', N'PRICING_COMPILED_RATE_CELL', 'TABLE', N'Purpose: Store package rating values in the lookup form used by SQL scoring.
One row: One compiled lookup key and multiplier for a package term.
Use: Derived from normalized rating tables during publication. This avoids rebuilding the joins on every score.'),
    (N'pricing', N'PRICING_FEATURE', 'TABLE', N'Purpose: Name an input used by a rating model, such as driver age or region.
One row: One reusable feature name and value type.
Use: A feature is an input variable. Model terms describe its main effect or its interaction with other inputs.'),
    (N'pricing', N'PRICING_FEATURE_LEVEL', 'TABLE', N'Purpose: Define a category or numeric band within a feature level set.
One row: One level code, label, ordering position, and optional numeric bounds.
Use: For example, a region category or an age band. Missing and other levels are explicit when exported.'),
    (N'pricing', N'PRICING_FEATURE_LEVEL_SET', 'TABLE', N'Purpose: Version the categories or numeric bands available for one rating feature.
One row: One named level set for a feature and model.
Use: Packages refer to a specific set so later changes do not redefine older rating values.'),
    (N'pricing', N'PRICING_MODEL', 'TABLE', N'Purpose: Register a named business model, such as motor claim frequency.
One row: One stable model identity, target, label, and active or retired status.
Use: Versions belong to MODEL_RUN and PRICING_RATE_PACKAGE. An active model is not necessarily deployed.'),
    (N'pricing', N'PRICING_MODEL_DEPLOYMENT', 'TABLE', N'Purpose: Record which rating package serves each model and deployment slot over time.
One row: One deployment interval for a model, slot, and package.
Use: The row with effective_to_ts IS NULL is current. Closed rows retain deployment history; a package can be deployed more than once.'),
    (N'pricing', N'PRICING_MODEL_VERSION_RESERVATION', 'TABLE', N'Purpose: Allocate model version names safely when builds run concurrently.
One row: One reserved model version for a model and export identifier.
Use: Internal allocation record. Do not infer publication or deployment from a reservation.'),
    (N'pricing', N'PRICING_RATE_CELL', 'TABLE', N'Purpose: Store one rating multiplier for a category, band, or combination of levels.
One row: One lookup entry within a package term, with a multiplier, log coefficient, and supporting weight.
Use: A rate cell is a rating value, not a policy record. A multiplier of 1.12 raises the base rate by 12 percent for that effect. Its levels are in PRICING_RATE_CELL_LEVEL.'),
    (N'pricing', N'PRICING_RATE_CELL_LEVEL', 'TABLE', N'Purpose: Identify the feature levels to which a rating multiplier applies.
One row: One feature level at one position in a rating-cell lookup key.
Use: A main-effect cell usually has one level. An interaction cell has one level for each participating feature.'),
    (N'pricing', N'PRICING_RATE_PACKAGE', 'TABLE', N'Purpose: Store the header of an immutable version of a rating model.
One row: One package revision with a base rate, status, validity dates, and optional parent package.
Use: A PUBLISHED package is available for deployment. PRICING_MODEL_DEPLOYMENT identifies the selected package for each slot.'),
    (N'pricing', N'PRICING_TERM', 'TABLE', N'Purpose: Describe one effect in a rating model.
One row: One main effect, interaction, or exported offset term within a package.
Use: For example, driver age or driver age by region. sequence_no controls display and scoring order.'),
    (N'pricing', N'PRICING_TERM_FEATURE', 'TABLE', N'Purpose: List the input features used by a model effect.
One row: One feature and level-set reference at one position within a term.
Use: An interaction has more than one input. Position determines the order used to build its lookup key.'),
    (N'pricing', N'V_ACTIVE_MODEL', 'VIEW', N'Purpose: List business models whose registry status is ACTIVE.
One row: One active model identity.
Use: ACTIVE is a registry status. It does not mean the model has a published or deployed package.'),
    (N'pricing', N'V_CURRENT_1D_RATE_BAND', 'VIEW', N'Purpose: Inspect numeric rating bands for current deployments.
One row: One numeric band per open deployment and term.
Use: Contains numeric bands only. V_CURRENT_DEPLOYED_RELATIVITY also includes categorical and interaction rating values.'),
    (N'pricing', N'V_CURRENT_DATASET_CV_FOLD', 'VIEW', N'Purpose: Inspect folds for the most recently registered dataset and split set.
One row: One fold in the newest split set of the newest manifest for each dataset name.
Use: Newest means created_ts, not data-as-at or deployment. train_folds_json lists other fold labels, not exact training-row membership; use the verified split artifact for that.'),
    (N'pricing', N'V_CURRENT_DEPLOYED_RELATIVITY', 'VIEW', N'Purpose: Inspect rating multipliers for the current deployment of each model and slot.
One row: One rating entry per open deployment of a PUBLISHED package.
Use: Includes deployment details and dataset context. The same package can appear in several slots; include deployment_slot when comparing results.'),
    (N'pricing', N'V_CURRENT_RATE_CELL', 'VIEW', N'Purpose: Inspect compiled rating lookup values for current deployments.
One row: One compiled rating entry per open deployment and term.
Use: A package deployed in two slots appears twice. For analyst comparisons, use V_CURRENT_DEPLOYED_RELATIVITY.'),
    (N'pricing', N'V_CURRENT_RATE_PACKAGE', 'VIEW', N'Purpose: Resolve the current package for each model and deployment slot.
One row: One open deployment, with model and package details.
Use: Current means effective_to_ts IS NULL. PREDICT_CURRENT_RATE uses this view to select the scoring package.'),
    (N'pricing', N'V_FINAL_MODEL_RELATIVITY', 'VIEW', N'Purpose: Compare package rating multipliers with their model and dataset context.
One row: One numeric band or categorical or interaction lookup entry, enriched with dataset and validation lineage.
Use: Final describes the exported package model. It does not mean latest, published, approved, or deployed. Includes all statuses; use candidate or deployed views when state matters. relativity is the multiplier applied for this effect.'),
    (N'pricing', N'V_MODEL_CANDIDATE_RELATIVITY', 'VIEW', N'Purpose: Compare rating multipliers across published model packages.
One row: One rating entry within a PUBLISHED package, with dataset and validation context.
Use: Includes historical published packages. Publication does not mean deployment. Use V_CURRENT_DEPLOYED_RELATIVITY for the selected package in each slot.'),
    (N'pricing', N'V_MODEL_LINEAGE_REDUNDANCY_CHECK', 'VIEW', N'Purpose: Find disagreements in stored model-run dataset and validation links.
One row: One model run joined to a package, with a diagnostic status.
Use: Filter redundancy_status <> OK to investigate missing, extra, or conflicting links. OK covers these link checks only; it does not verify artifacts or every integrity rule.'),
    (N'pricing', N'V_MODEL_MONITORING_LAMBDA', 'VIEW', N'Purpose: Compare smoothing penalties across monitoring observations.
One row: One smoothing component within a monitoring observation.
Use: lambda_mode distinguishes baseline, fixed, and estimated values. Compare within the same baseline contract.'),
    (N'pricing', N'V_MODEL_MONITORING_RELATIVITY', 'VIEW', N'Purpose: Compare monitoring multipliers on the baseline feature grid.
One row: One term comparison point within a monitoring observation.
Use: Use baseline deployment, component, variant, and data-as-at to compare like-for-like observations. These multipliers are diagnostic, not deployable.'),
    (N'pricing', N'V_MODEL_MONITORING_RUN', 'VIEW', N'Purpose: Compare monitoring observations with their deployed baseline and dated dataset.
One row: One recorded monitoring observation for a component and variant.
Use: Includes historical baseline deployments, status, and stored evidence digests. These observations are not candidate packages.'),
    (N'pricing', N'V_MODEL_RELATIVITY', 'VIEW', N'Purpose: Combine numeric bands and other rating entries into one internal representation.
One row: One numeric band or categorical or interaction lookup entry within a model package.
Use: Includes all package statuses and versions. Both branches describe the package model. Analysts should use V_FINAL_MODEL_RELATIVITY for dataset and validation context.'),
    (N'pricing', N'V_MODEL_VALIDATION_SPLIT', 'VIEW', N'Purpose: Compare held-out validation performance fold by fold.
One row: One fold with recorded metrics for a successful model run and its validation split set.
Use: Includes deviance, negative log-likelihood, and Gini where recorded. Runs without fold metrics are absent.'),
    (N'pricing', N'V_MODEL_VALIDATION_SUMMARY', 'VIEW', N'Purpose: Compare validation performance across recorded model runs.
One row: One model run represented in the fold-validation view, with run-level and fold summaries.
Use: Pooled metrics come from held-out predictions across folds. They are not generally the average of fold metrics. Runs without fold evidence are absent.'),
    (N'pricing', N'V_PUBLISHED_MODEL_RELATIVITY', 'VIEW', N'Purpose: Provide the compatibility name for published candidate rating multipliers.
One row: The same rating entries and columns as V_MODEL_CANDIDATE_RELATIVITY.
Use: New queries should use V_MODEL_CANDIDATE_RELATIVITY. This name remains for existing SQL consumers.'),
    (N'pricing_stg', N'STG_CELL_LEVEL', 'TABLE', N'Purpose: Temporarily hold the feature levels that identify each staged rating entry.
One row: One level at one feature position within a staged workbook entry.
Use: Publication uses these rows to build category, band, and interaction lookup keys. Successful publication removes them.'),
    (N'pricing_stg', N'STG_RATE_CELL', 'TABLE', N'Purpose: Temporarily hold rating multipliers read from an export workbook.
One row: One workbook rating entry within an export attempt.
Use: Publication validates and copies these rows into a package, then removes them on success.'),
    (N'pricing_stg', N'STG_RATING_EXPORT', 'TABLE', N'Purpose: Receive the header and receipt for a workbook publication attempt.
One row: One export identifier with model metadata, hashes, and base rate.
Use: Successful publication removes the staged child rows but retains this header as a retry receipt. Its presence alone does not mean a package was published.'),
    (N'pricing_stg', N'STG_TERM_METADATA', 'TABLE', N'Purpose: Temporarily hold model-effect metadata from an export workbook.
One row: One metadata JSON document for a term within an export attempt.
Use: Publication uses this evidence to preserve effect types and exported model behavior. Successful publication removes it.');

DECLARE @schema_name SYSNAME, @object_name SYSNAME, @object_type VARCHAR(5);
DECLARE @description NVARCHAR(3500), @object_id INT;
DECLARE description_cursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT schema_name, object_name, object_type, description
    FROM @object_descriptions;
OPEN description_cursor;
FETCH NEXT FROM description_cursor INTO @schema_name, @object_name, @object_type, @description;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @object_id = OBJECT_ID(QUOTENAME(@schema_name) + N'.' + QUOTENAME(@object_name));
    IF @object_id IS NULL
    BEGIN;
        THROW 51042, 'Cannot document schema: an expected table or view is missing.', 1;
    END;
    IF EXISTS (
        SELECT 1 FROM sys.extended_properties
        WHERE class = 1 AND major_id = @object_id AND minor_id = 0
          AND name = N'MS_Description'
    )
        EXEC sys.sp_updateextendedproperty
            @name = N'MS_Description', @value = @description,
            @level0type = N'SCHEMA', @level0name = @schema_name,
            @level1type = @object_type, @level1name = @object_name;
    ELSE
        EXEC sys.sp_addextendedproperty
            @name = N'MS_Description', @value = @description,
            @level0type = N'SCHEMA', @level0name = @schema_name,
            @level1type = @object_type, @level1name = @object_name;
    FETCH NEXT FROM description_cursor INTO @schema_name, @object_name, @object_type, @description;
END;
CLOSE description_cursor;
DEALLOCATE description_cursor;
GO
