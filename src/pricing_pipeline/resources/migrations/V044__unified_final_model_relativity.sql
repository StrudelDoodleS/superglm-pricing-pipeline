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
LEFT JOIN mlops.MODEL_RUN_DATASET AS run_dataset
  ON run_dataset.model_run_id = model_run.model_run_id
 AND run_dataset.dataset_role = 'training'
 AND run_dataset.manifest_id = model_run.manifest_id
LEFT JOIN pricing.DATASET_MANIFEST AS manifest
  ON manifest.manifest_id = COALESCE(run_dataset.manifest_id, model_run.manifest_id)
LEFT JOIN validation_split_links AS validation_split
  ON validation_split.model_run_id = model_run.model_run_id;
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

EXEC sys.sp_updateextendedproperty
    @name=N'MS_Description',
    @value=N'Purpose: Inspect every exported model effect with model and dataset dates. One row: One lookup, numeric coefficient, per-unit factor, or spline segment. Use: SPLINE stores the exact fitted log-effect polynomial a+u*(b+u*(c+u*d)), u=(x-lower_bound)/(upper_bound-lower_bound). Relativity is EXP(log effect); NULL bounds use EXP(a). Fixed relativity and log_coefficient are NULL for splines. Includes all statuses and model versions.',
    @level0type=N'SCHEMA', @level0name=N'pricing',
    @level1type=N'VIEW', @level1name=N'V_FINAL_MODEL_RELATIVITY';
GO
