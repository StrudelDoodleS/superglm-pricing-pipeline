-- Exact one-dimensional spline main effects. Existing lookup packages keep their representation.
IF COL_LENGTH('pricing_stg.STG_RATE_CELL', 'spline_a') IS NULL
    ALTER TABLE pricing_stg.STG_RATE_CELL ADD spline_a FLOAT NULL;
GO

IF COL_LENGTH('pricing_stg.STG_RATE_CELL', 'spline_b') IS NULL
    ALTER TABLE pricing_stg.STG_RATE_CELL ADD spline_b FLOAT NULL;
GO

IF COL_LENGTH('pricing_stg.STG_RATE_CELL', 'spline_c') IS NULL
    ALTER TABLE pricing_stg.STG_RATE_CELL ADD spline_c FLOAT NULL;
GO

IF COL_LENGTH('pricing_stg.STG_RATE_CELL', 'spline_d') IS NULL
    ALTER TABLE pricing_stg.STG_RATE_CELL ADD spline_d FLOAT NULL;
GO

IF COL_LENGTH('pricing_stg.STG_RATE_CELL', 'spline_lower') IS NULL
    ALTER TABLE pricing_stg.STG_RATE_CELL ADD spline_lower FLOAT NULL;
GO

IF COL_LENGTH('pricing_stg.STG_RATE_CELL', 'spline_upper') IS NULL
    ALTER TABLE pricing_stg.STG_RATE_CELL ADD spline_upper FLOAT NULL;
GO

IF COL_LENGTH('pricing_stg.STG_RATE_CELL', 'spline_upper_inclusive') IS NULL
    ALTER TABLE pricing_stg.STG_RATE_CELL ADD spline_upper_inclusive BIT NULL;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('pricing.PRICING_TERM')
      AND name = 'UX_PRICING_TERM_PACKAGE_TERM'
)
    CREATE UNIQUE INDEX UX_PRICING_TERM_PACKAGE_TERM
    ON pricing.PRICING_TERM(rate_package_id, term_id);
GO

IF OBJECT_ID('pricing.PRICING_SPLINE_SEGMENT', 'U') IS NULL
CREATE TABLE pricing.PRICING_SPLINE_SEGMENT (
    rate_package_id BIGINT NOT NULL,
    term_id BIGINT NOT NULL,
    segment_order INT NOT NULL,
    feature_name NVARCHAR(128) NOT NULL,
    level_label NVARCHAR(256) NULL,
    lower_bound FLOAT NULL,
    upper_bound FLOAT NULL,
    upper_inclusive BIT NOT NULL,
    a FLOAT NOT NULL,
    b FLOAT NOT NULL,
    c FLOAT NOT NULL,
    d FLOAT NOT NULL,
    exposure_weight FLOAT NULL,
    CONSTRAINT PK_PRICING_SPLINE_SEGMENT PRIMARY KEY (rate_package_id, term_id, segment_order),
    CONSTRAINT FK_PRICING_SPLINE_SEGMENT_TERM FOREIGN KEY (rate_package_id, term_id)
        REFERENCES pricing.PRICING_TERM(rate_package_id, term_id),
    CONSTRAINT CK_PRICING_SPLINE_SEGMENT_INTERVAL
        CHECK (lower_bound IS NULL OR upper_bound IS NULL OR lower_bound < upper_bound),
    CONSTRAINT CK_PRICING_SPLINE_SEGMENT_TAIL
        CHECK ((lower_bound IS NOT NULL AND upper_bound IS NOT NULL) OR (b = 0 AND c = 0 AND d = 0)),
    CONSTRAINT CK_PRICING_SPLINE_SEGMENT_BOUND
        CHECK (lower_bound IS NOT NULL OR upper_bound IS NOT NULL)
);
GO

CREATE OR ALTER VIEW pricing.V_MODEL_SPLINE_SEGMENT AS
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
    mr.model_equivalence_sha256, mr.export_id, mr.manifest_id, validation_split.split_set_id,
    dm.dataset_name, dm.source_system, dm.data_as_of_date, dm.row_count AS dataset_row_count,
    rp.rate_package_id, rp.parent_rate_package_id, rp.model_version, rp.package_version,
    rp.base_rate, rp.package_status, rp.effective_from_date, rp.effective_to_date,
    rp.package_metadata_json,
    JSON_QUERY(rp.package_metadata_json, '$.input_preparation.transforms') AS transforms_json,
    t.term_id, t.term_name, t.term_type, t.sequence_no AS term_sequence_no, t.term_metadata_json,
    s.segment_order, s.feature_name, s.level_label,
    s.lower_bound, s.upper_bound, s.upper_inclusive, s.a, s.b, s.c, s.d, s.exposure_weight
FROM pricing.PRICING_SPLINE_SEGMENT AS s
JOIN pricing.PRICING_TERM AS t ON t.term_id = s.term_id AND t.rate_package_id = s.rate_package_id
JOIN pricing.PRICING_RATE_PACKAGE AS rp ON rp.rate_package_id = s.rate_package_id
JOIN pricing.PRICING_MODEL AS m ON m.model_id = rp.model_id
LEFT JOIN pricing.MODEL_RUN AS mr ON mr.rate_package_id = rp.rate_package_id
LEFT JOIN pricing.DATASET_MANIFEST AS dm ON dm.manifest_id = mr.manifest_id
LEFT JOIN (
    SELECT model_run_id, manifest_id, MAX(split_set_id) AS split_set_id
    FROM mlops.MODEL_RUN_SPLIT_SET
    WHERE dataset_role = 'training' AND split_role = 'validation'
    GROUP BY model_run_id, manifest_id
    HAVING COUNT(*) = 1
) AS validation_split
  ON validation_split.model_run_id = mr.model_run_id
 AND validation_split.manifest_id = mr.manifest_id;
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
WHERE c.term_type <> 'SPLINE_PPOLY_1D'
AND NOT EXISTS (
    SELECT 1
    FROM pricing.PRICING_COMPILED_1D_RATE_BAND AS b
    WHERE b.rate_package_id = c.rate_package_id
      AND b.term_id = c.term_id
);
GO

CREATE OR ALTER PROCEDURE pricing.PREDICT_RATE_PACKAGE
    @rate_package_id BIGINT,
    @features_json NVARCHAR(MAX),
    @exposure FLOAT = 1.0,
    @include_breakdown BIT = 0
AS
/*
Purpose: Score one exact rating package from its exported lookup and polynomial effects.
Numeric effects stay on the log scale until the complete model is combined.
For a requested breakdown, a numeric multiplier outside the documented SQL
FLOAT range is NULL; log_coefficient still contains its log contribution.
The combined score can remain finite when individual effects exceed that range.
*/
BEGIN
    SET NOCOUNT ON;

    IF ISJSON(@features_json) <> 1
    BEGIN;
        THROW 50000, 'features_json must be valid JSON', 1;
    END;

    IF @exposure IS NULL OR @exposure <= 0
    BEGIN;
        THROW 50001, 'exposure must be positive', 1;
    END;

    DECLARE @model_name NVARCHAR(128);
    DECLARE @base_rate FLOAT;
    DECLARE @required_terms INT;
    DECLARE @matched_terms INT;

    SELECT
        @model_name = model_name,
        @base_rate = CAST(base_rate AS FLOAT)
    FROM pricing.PRICING_RATE_PACKAGE
    WHERE rate_package_id = @rate_package_id
      AND package_status IN ('DRAFT', 'PUBLISHED');

    IF @model_name IS NULL
    BEGIN;
        THROW 50002, 'Rate package is not available for explicit scoring', 1;
    END;

    DECLARE @matched TABLE (
        term_id BIGINT NOT NULL PRIMARY KEY,
        term_name NVARCHAR(128) NOT NULL,
        term_type NVARCHAR(64) NOT NULL,
        match_type NVARCHAR(32) NOT NULL,
        feature_name NVARCHAR(128) NOT NULL,
        input_value NVARCHAR(4000) NULL,
        level_code NVARCHAR(128) NULL,
        multiplier FLOAT NULL,
        log_coefficient FLOAT NOT NULL
    );

    -- SQL inputs are prepared feature values; transforms remain the caller's responsibility.
    -- Each segment is half-open, except an explicitly inclusive final finite endpoint.
    WITH spline_input AS (
        SELECT
            segment.*,
            term.term_name,
            term.term_type,
            JSON_VALUE(@features_json, CONCAT('$.', segment.feature_name)) AS input_value
        FROM pricing.PRICING_SPLINE_SEGMENT AS segment
        JOIN pricing.PRICING_TERM AS term
          ON term.term_id = segment.term_id
         AND term.rate_package_id = segment.rate_package_id
        WHERE segment.rate_package_id = @rate_package_id
          AND term.term_type = 'SPLINE_PPOLY_1D'
    ), spline_numeric AS (
        SELECT *, TRY_CONVERT(FLOAT, input_value) AS numeric_value
        FROM spline_input
    ), spline_coordinate AS (
        SELECT *,
            CASE WHEN lower_bound IS NULL OR upper_bound IS NULL THEN 0.0
                 ELSE (numeric_value - lower_bound) / NULLIF(upper_bound - lower_bound, 0.0)
            END AS u
        FROM spline_numeric
        WHERE numeric_value IS NOT NULL
          AND (lower_bound IS NULL OR numeric_value >= lower_bound)
          AND (upper_bound IS NULL OR numeric_value < upper_bound
               OR (upper_inclusive = 1 AND numeric_value = upper_bound))
    )
    INSERT INTO @matched (
        term_id, term_name, term_type, match_type, feature_name,
        input_value, level_code, multiplier, log_coefficient
    )
    SELECT
        term_id, term_name, term_type, 'SPLINE', feature_name,
        input_value, CONVERT(NVARCHAR(128), segment_order), CAST(NULL AS FLOAT),
        a + u * (b + u * (c + u * d))
    FROM spline_coordinate;

    INSERT INTO @matched (
        term_id,
        term_name,
        term_type,
        match_type,
        feature_name,
        input_value,
        level_code,
        multiplier,
        log_coefficient
    )
    SELECT
        term.term_id,
        band.term_name,
        term.term_type,
        'BAND',
        band.feature_name,
        JSON_VALUE(@features_json, CONCAT('$.', band.feature_name)),
        band.level_code,
        CAST(band.multiplier AS FLOAT),
        CAST(band.log_coefficient AS FLOAT)
    FROM (
        SELECT DISTINCT
            term_id,
            term_name,
            term_type
        FROM pricing.PRICING_COMPILED_RATE_CELL
        WHERE rate_package_id = @rate_package_id
    ) AS term
    CROSS APPLY (
        SELECT TOP (1) band.*
        FROM pricing.PRICING_COMPILED_1D_RATE_BAND AS band
        WHERE band.rate_package_id = @rate_package_id
          AND band.term_id = term.term_id
          AND TRY_CONVERT(
              FLOAT,
              JSON_VALUE(@features_json, CONCAT('$.', band.feature_name))
          ) IS NOT NULL
          AND TRY_CONVERT(
              FLOAT,
              JSON_VALUE(@features_json, CONCAT('$.', band.feature_name))
          ) >= band.lower_bound
          AND (
              band.upper_bound IS NULL
              OR TRY_CONVERT(
                  FLOAT,
                  JSON_VALUE(@features_json, CONCAT('$.', band.feature_name))
              ) < band.upper_bound
          )
        ORDER BY band.sort_order, band.feature_level_id
    ) AS band;

    INSERT INTO @matched (
        term_id,
        term_name,
        term_type,
        match_type,
        feature_name,
        input_value,
        level_code,
        multiplier,
        log_coefficient
    )
    SELECT
        cell.term_id,
        cell.term_name,
        cell.term_type,
        'NUMERIC',
        term_feature.input_column_name,
        raw_input.input_value,
        feature_level.level_code,
        CAST(NULL AS FLOAT),
        numeric_input.numeric_value * CAST(cell.log_coefficient AS FLOAT)
    FROM pricing.PRICING_COMPILED_RATE_CELL AS cell
    JOIN pricing.PRICING_RATE_CELL AS source_cell
      ON source_cell.term_id = cell.term_id
     AND source_cell.cell_key_digest = cell.cell_key_digest
    JOIN pricing.PRICING_TERM_FEATURE AS term_feature
      ON term_feature.term_id = cell.term_id
     AND term_feature.position_no = 1
    JOIN pricing.PRICING_RATE_CELL_LEVEL AS cell_level
      ON cell_level.cell_id = source_cell.cell_id
     AND cell_level.position_no = term_feature.position_no
    JOIN pricing.PRICING_FEATURE_LEVEL AS feature_level
      ON feature_level.feature_level_id = cell_level.feature_level_id
     AND feature_level.level_set_id = term_feature.level_set_id
    CROSS APPLY (
        SELECT JSON_VALUE(
            @features_json,
            CONCAT('$.', term_feature.input_column_name)
        ) AS input_value
    ) AS raw_input
    CROSS APPLY (
        SELECT TRY_CONVERT(FLOAT, raw_input.input_value) AS numeric_value
    ) AS numeric_input
    WHERE cell.rate_package_id = @rate_package_id
      AND cell.term_type = 'NUMERIC_MAIN'
      AND LOWER(feature_level.level_code) = 'per_unit'
      AND numeric_input.numeric_value IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM @matched AS matched
          WHERE matched.term_id = cell.term_id
      );

    INSERT INTO @matched (
        term_id,
        term_name,
        term_type,
        match_type,
        feature_name,
        input_value,
        level_code,
        multiplier,
        log_coefficient
    )
    SELECT
        cell.term_id,
        cell.term_name,
        cell.term_type,
        'INTERACTION',
        cell.term_name,
        cell.cell_key_text,
        cell.cell_key_text,
        CAST(cell.multiplier AS FLOAT),
        CAST(cell.log_coefficient AS FLOAT)
    FROM pricing.PRICING_COMPILED_RATE_CELL AS cell
    JOIN pricing.PRICING_RATE_CELL AS source_cell
      ON source_cell.term_id = cell.term_id
     AND source_cell.cell_key_digest = cell.cell_key_digest
    WHERE cell.rate_package_id = @rate_package_id
      AND cell.term_type = 'CATEGORICAL_INTERACTION'
      AND 2 = (
          SELECT COUNT(*)
          FROM pricing.PRICING_TERM_FEATURE AS term_feature
          WHERE term_feature.term_id = cell.term_id
      )
      AND 2 = (
          SELECT COUNT(*)
          FROM pricing.PRICING_RATE_CELL_LEVEL AS cell_level
          WHERE cell_level.cell_id = source_cell.cell_id
      )
      AND NOT EXISTS (
          SELECT 1
          FROM pricing.PRICING_TERM_FEATURE AS term_feature
          WHERE term_feature.term_id = cell.term_id
            AND NOT EXISTS (
                SELECT 1
                FROM pricing.PRICING_RATE_CELL_LEVEL AS cell_level
                JOIN pricing.PRICING_FEATURE_LEVEL AS feature_level
                  ON feature_level.feature_level_id = cell_level.feature_level_id
                 AND feature_level.level_set_id = term_feature.level_set_id
                WHERE cell_level.cell_id = source_cell.cell_id
                  AND cell_level.position_no = term_feature.position_no
                  AND feature_level.level_code = JSON_VALUE(
                      @features_json,
                      CONCAT('$.', term_feature.input_column_name)
                  )
            )
      )
      AND NOT EXISTS (
          SELECT 1
          FROM @matched AS matched
          WHERE matched.term_id = cell.term_id
      );

    INSERT INTO @matched (
        term_id,
        term_name,
        term_type,
        match_type,
        feature_name,
        input_value,
        level_code,
        multiplier,
        log_coefficient
    )
    SELECT
        cell.term_id,
        cell.term_name,
        cell.term_type,
        'CELL',
        cell.term_name,
        JSON_VALUE(@features_json, CONCAT('$.', cell.term_name)),
        cell.cell_key_text,
        CAST(cell.multiplier AS FLOAT),
        CAST(cell.log_coefficient AS FLOAT)
    FROM pricing.PRICING_COMPILED_RATE_CELL AS cell
    WHERE cell.rate_package_id = @rate_package_id
      AND cell.term_type NOT IN ('NUMERIC_MAIN', 'CATEGORICAL_INTERACTION', 'SPLINE_PPOLY_1D')
      AND NOT EXISTS (
          SELECT 1
          FROM @matched AS matched
          WHERE matched.term_id = cell.term_id
      )
      AND cell.cell_key_text = CONCAT(
          cell.term_name,
          '=',
          JSON_VALUE(@features_json, CONCAT('$.', cell.term_name))
      );

    INSERT INTO @matched (
        term_id,
        term_name,
        term_type,
        match_type,
        feature_name,
        input_value,
        level_code,
        multiplier,
        log_coefficient
    )
    SELECT
        cell.term_id,
        cell.term_name,
        cell.term_type,
        'DEFAULT',
        cell.term_name,
        JSON_VALUE(@features_json, CONCAT('$.', cell.term_name)),
        cell.cell_key_text,
        CAST(cell.multiplier AS FLOAT),
        CAST(cell.log_coefficient AS FLOAT)
    FROM pricing.PRICING_COMPILED_RATE_CELL AS cell
    WHERE cell.rate_package_id = @rate_package_id
      AND cell.term_type NOT IN ('NUMERIC_MAIN', 'CATEGORICAL_INTERACTION', 'SPLINE_PPOLY_1D')
      AND cell.is_default = 1
      AND NOT EXISTS (
          SELECT 1
          FROM @matched AS matched
          WHERE matched.term_id = cell.term_id
      );

    SELECT @required_terms = COUNT(DISTINCT term_id)
    FROM pricing.PRICING_COMPILED_RATE_CELL
    WHERE rate_package_id = @rate_package_id;

    SELECT @matched_terms = COUNT(*)
    FROM @matched;

    IF @matched_terms <> @required_terms
    BEGIN;
        THROW 50003, 'Input features did not match every required term', 1;
    END;

    SELECT
        @model_name AS model_name,
        @rate_package_id AS rate_package_id,
        @base_rate AS base_rate,
        @exposure AS exposure,
        EXP(SUM(log_coefficient)) AS relativity,
        @base_rate * @exposure * EXP(SUM(log_coefficient)) AS prediction,
        @required_terms AS required_terms,
        @matched_terms AS matched_terms
    FROM @matched;

    IF @include_breakdown = 1
    BEGIN
        SELECT
            term_id,
            term_name,
            term_type,
            match_type,
            feature_name,
            input_value,
            level_code,
            CASE WHEN match_type IN ('NUMERIC', 'SPLINE') THEN
                -- Guard the argument itself so EXP never receives an unsafe value.
                -- Bounds follow the documented positive SQL FLOAT range.
                EXP(CASE
                    WHEN log_coefficient BETWEEN LOG(2.23E-308) AND LOG(1.79E308)
                    THEN log_coefficient
                    ELSE NULL
                END)
            ELSE multiplier END AS multiplier,
            log_coefficient
        FROM @matched
        ORDER BY term_id;
    END;
END;
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Purpose: Preserve exact one-dimensional spline log effects. One row: One ordered polynomial segment within a package term. Use: Evaluate a+u*(b+u*(c+u*d)), u=(x-lower_bound)/(upper_bound-lower_bound); NULL bounds are constant tails. Coefficients and bounds are double precision.',
    @level0type = N'SCHEMA', @level0name = N'pricing',
    @level1type = N'TABLE', @level1name = N'PRICING_SPLINE_SEGMENT';
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Purpose: Inspect exact spline segments with model/run/dataset lineage and preparation metadata. One row: One package term segment across all statuses. Use: Prepare feature_name with transforms_json and evaluate the normalized polynomial; rows are not constant interval relativities.',
    @level0type = N'SCHEMA', @level0name = N'pricing',
    @level1type = N'VIEW', @level1name = N'V_MODEL_SPLINE_SEGMENT';
GO

CREATE OR ALTER TRIGGER pricing.TR_PRICING_SPLINE_SEGMENT_IMMUTABLE_WRITE
ON pricing.PRICING_SPLINE_SEGMENT
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM (
            SELECT rate_package_id FROM inserted
            UNION
            SELECT rate_package_id FROM deleted
        ) changed
        JOIN pricing.PRICING_RATE_PACKAGE rp
          ON rp.rate_package_id = changed.rate_package_id
        WHERE rp.package_status <> 'DRAFT'
           OR EXISTS (
               SELECT 1
               FROM pricing.PRICING_MODEL_DEPLOYMENT md
               WHERE md.rate_package_id = rp.rate_package_id
           )
    )
    BEGIN;
        THROW 51000, 'Immutable rate packages cannot be changed directly. Create a new package revision.', 1;
    END;
END;
GO
