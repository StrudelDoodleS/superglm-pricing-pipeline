CREATE TABLE pricing.MODEL_MONITORING_BASELINE (
    model_run_id BIGINT NOT NULL,
    model_id BIGINT NOT NULL,
    rate_package_id BIGINT NOT NULL,
    capture_status VARCHAR(16) NOT NULL,
    unavailable_reason NVARCHAR(2000) NULL,
    snapshot_schema_version INT NULL,
    snapshot_json NVARCHAR(MAX) NULL,
    snapshot_sha256 CHAR(64) COLLATE Latin1_General_100_BIN2 NULL,
    superglm_version NVARCHAR(128) NULL,
    source_lineage_json NVARCHAR(MAX) NOT NULL,
    source_lineage_sha256 CHAR(64) COLLATE Latin1_General_100_BIN2 NOT NULL,
    created_ts DATETIME2(3) NOT NULL CONSTRAINT DF_MODEL_MONITORING_BASELINE_CREATED_TS DEFAULT SYSUTCDATETIME(),
    created_by NVARCHAR(128) NOT NULL,
    CONSTRAINT PK_MODEL_MONITORING_BASELINE PRIMARY KEY (model_run_id),
    CONSTRAINT FK_MODEL_MONITORING_BASELINE_RUN FOREIGN KEY (model_run_id) REFERENCES pricing.MODEL_RUN(model_run_id),
    CONSTRAINT FK_MODEL_MONITORING_BASELINE_MODEL FOREIGN KEY (model_id) REFERENCES pricing.PRICING_MODEL(model_id),
    CONSTRAINT FK_MODEL_MONITORING_BASELINE_PACKAGE FOREIGN KEY (rate_package_id) REFERENCES pricing.PRICING_RATE_PACKAGE(rate_package_id),
    CONSTRAINT CK_MODEL_MONITORING_BASELINE_STATUS CHECK (
        (capture_status='CAPTURED' AND unavailable_reason IS NULL
         AND snapshot_schema_version IS NOT NULL AND snapshot_schema_version>=1
         AND snapshot_json IS NOT NULL AND snapshot_sha256 IS NOT NULL AND superglm_version IS NOT NULL)
        OR (capture_status='UNAVAILABLE' AND unavailable_reason IS NOT NULL AND LEN(LTRIM(RTRIM(unavailable_reason)))>0
            AND snapshot_schema_version IS NULL AND snapshot_json IS NULL AND snapshot_sha256 IS NULL AND superglm_version IS NULL)
    ),
    CONSTRAINT CK_MODEL_MONITORING_BASELINE_JSON CHECK (snapshot_json IS NULL OR (ISJSON(snapshot_json)=1 AND LEFT(LTRIM(snapshot_json),1)='{')),
    CONSTRAINT CK_MODEL_MONITORING_BASELINE_SHA256 CHECK (snapshot_sha256 IS NULL OR (LEN(snapshot_sha256)=64 AND snapshot_sha256 NOT LIKE '%[^0-9a-f]%')),
    CONSTRAINT CK_MODEL_MONITORING_BASELINE_SOURCE_JSON CHECK (ISJSON(source_lineage_json)=1 AND LEFT(LTRIM(source_lineage_json),1)='{'),
    CONSTRAINT CK_MODEL_MONITORING_BASELINE_SOURCE_SHA256 CHECK (LEN(source_lineage_sha256)=64 AND source_lineage_sha256 NOT LIKE '%[^0-9a-f]%')
);
GO

CREATE OR ALTER TRIGGER pricing.TR_MODEL_MONITORING_BASELINE_LINEAGE_GUARD
ON pricing.MODEL_MONITORING_BASELINE AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1 FROM inserted AS baseline WHERE NOT EXISTS (
            SELECT 1 FROM pricing.MODEL_RUN AS mr JOIN pricing.PRICING_RATE_PACKAGE AS rp
              ON rp.rate_package_id=mr.rate_package_id AND rp.model_id=mr.model_id
            WHERE mr.model_run_id=baseline.model_run_id AND mr.model_id=baseline.model_id
              AND mr.rate_package_id=baseline.rate_package_id AND mr.run_status='SUCCESS'
              AND rp.package_status='PUBLISHED'
        )
    )
        THROW 51049, 'A monitoring baseline must identify one successful published model run.', 1;
END;
GO

CREATE OR ALTER TRIGGER pricing.TR_MODEL_MONITORING_BASELINE_IMMUTABLE
ON pricing.MODEL_MONITORING_BASELINE AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (SELECT 1 FROM deleted)
        THROW 51050, 'Monitoring baselines are immutable.', 1;
END;
GO

CREATE OR ALTER TRIGGER pricing.TR_MODEL_RUN_BASELINE_IDENTITY
ON pricing.MODEL_RUN AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT historical.model_run_id, historical.model_id, historical.rate_package_id,
            historical.run_status COLLATE Latin1_General_100_BIN2,
            historical.model_version COLLATE Latin1_General_100_BIN2,
            historical.model_kind COLLATE Latin1_General_100_BIN2,
            historical.export_id COLLATE Latin1_General_100_BIN2,
            historical.manifest_id COLLATE Latin1_General_100_BIN2,
            historical.publication_receipt_sha256 COLLATE Latin1_General_100_BIN2,
            historical.model_source_sha256 COLLATE Latin1_General_100_BIN2,
            historical.model_equivalence_sha256 COLLATE Latin1_General_100_BIN2,
            historical.candidate_artifact_sha256 COLLATE Latin1_General_100_BIN2,
            historical.candidate_artifact_format COLLATE Latin1_General_100_BIN2,
            historical.candidate_artifact_size_bytes,
            historical.candidate_python_version COLLATE Latin1_General_100_BIN2,
            historical.candidate_superglm_version COLLATE Latin1_General_100_BIN2,
            historical.rating_workbook_sha256 COLLATE Latin1_General_100_BIN2
        FROM deleted AS historical
        JOIN pricing.MODEL_MONITORING_BASELINE AS baseline ON baseline.model_run_id=historical.model_run_id
        EXCEPT
        SELECT current_run.model_run_id, current_run.model_id, current_run.rate_package_id,
            current_run.run_status COLLATE Latin1_General_100_BIN2,
            current_run.model_version COLLATE Latin1_General_100_BIN2,
            current_run.model_kind COLLATE Latin1_General_100_BIN2,
            current_run.export_id COLLATE Latin1_General_100_BIN2,
            current_run.manifest_id COLLATE Latin1_General_100_BIN2,
            current_run.publication_receipt_sha256 COLLATE Latin1_General_100_BIN2,
            current_run.model_source_sha256 COLLATE Latin1_General_100_BIN2,
            current_run.model_equivalence_sha256 COLLATE Latin1_General_100_BIN2,
            current_run.candidate_artifact_sha256 COLLATE Latin1_General_100_BIN2,
            current_run.candidate_artifact_format COLLATE Latin1_General_100_BIN2,
            current_run.candidate_artifact_size_bytes,
            current_run.candidate_python_version COLLATE Latin1_General_100_BIN2,
            current_run.candidate_superglm_version COLLATE Latin1_General_100_BIN2,
            current_run.rating_workbook_sha256 COLLATE Latin1_General_100_BIN2
        FROM inserted AS current_run
    )
        THROW 51051, 'A model run referenced by a monitoring baseline retains its source identity.', 1;
END;
GO

CREATE OR ALTER TRIGGER pricing.TR_RATE_PACKAGE_BASELINE_IDENTITY
ON pricing.PRICING_RATE_PACKAGE AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT historical.rate_package_id, historical.model_id, historical.package_version,
            historical.model_version COLLATE Latin1_General_100_BIN2,
            historical.source_export_id COLLATE Latin1_General_100_BIN2,
            historical.publication_receipt_sha256 COLLATE Latin1_General_100_BIN2,
            historical.publication_receipt_json COLLATE Latin1_General_100_BIN2
        FROM deleted AS historical
        JOIN pricing.MODEL_MONITORING_BASELINE AS baseline ON baseline.rate_package_id=historical.rate_package_id
        EXCEPT
        SELECT current_package.rate_package_id, current_package.model_id, current_package.package_version,
            current_package.model_version COLLATE Latin1_General_100_BIN2,
            current_package.source_export_id COLLATE Latin1_General_100_BIN2,
            current_package.publication_receipt_sha256 COLLATE Latin1_General_100_BIN2,
            current_package.publication_receipt_json COLLATE Latin1_General_100_BIN2
        FROM inserted AS current_package
    )
        THROW 51052, 'A package referenced by a monitoring baseline retains its source identity.', 1;
END;
GO

EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Immutable JSON fitted state, reference summaries, and source lineage captured at publication for recurring SQL monitoring. Unsupported models record an unavailable reason. Historical publications are preserved and may be captured once without refitting.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'TABLE', @level1name=N'MODEL_MONITORING_BASELINE';
GO
