-- Stop old monitoring writers before applying this migration.
-- Historical observations are closed to new children, without certifying their evidence.
IF COL_LENGTH('mlops.MODEL_MONITOR_RUN', 'evidence_sealed') IS NULL
BEGIN
    ALTER TABLE mlops.MODEL_MONITOR_RUN ADD evidence_sealed BIT NOT NULL
        CONSTRAINT DF_MODEL_MONITOR_RUN_EVIDENCE_SEALED DEFAULT (1);
END;
GO

-- Replace the old INSTEAD OF trigger with an AFTER guard for the seal transition.
DROP TRIGGER IF EXISTS mlops.TR_MODEL_MONITOR_RUN_IMMUTABLE;
GO
CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_RUN_IMMUTABLE
ON mlops.MODEL_MONITOR_RUN
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM deleted AS old_run
        FULL OUTER JOIN inserted AS new_run
          ON new_run.monitor_run_id = old_run.monitor_run_id
        WHERE old_run.monitor_run_id IS NULL
           OR new_run.monitor_run_id IS NULL
           OR old_run.evidence_sealed <> 0
           OR new_run.evidence_sealed <> 1
    )
    BEGIN
        THROW 51023, 'Monitoring evidence is immutable; only an open observation may be sealed.', 1;
    END;
    -- Compare text as bytes so case and trailing spaces cannot change during sealing.
    IF EXISTS (
        SELECT
            monitor_run_id,
            fit_contract_id,
            baseline_deployment_id,
            model_id,
            rate_package_id,
            CONVERT(VARBINARY(MAX), manifest_id),
            CONVERT(VARBINARY(MAX), component_role),
            CONVERT(VARBINARY(MAX), variant_code),
            CONVERT(VARBINARY(MAX), run_signature_sha256),
            CONVERT(VARBINARY(MAX), run_status),
            CONVERT(VARBINARY(MAX), invariant_status),
            CONVERT(VARBINARY(MAX), invariant_evidence_sha256),
            CONVERT(VARBINARY(MAX), invariant_evidence_json),
            CONVERT(VARBINARY(MAX), model_frame_sha256),
            CONVERT(VARBINARY(MAX), fit_configuration_json),
            CONVERT(VARBINARY(MAX), result_evidence_sha256),
            started_ts,
            completed_ts,
            CONVERT(VARBINARY(MAX), created_by)
        FROM deleted
        EXCEPT
        SELECT
            monitor_run_id,
            fit_contract_id,
            baseline_deployment_id,
            model_id,
            rate_package_id,
            CONVERT(VARBINARY(MAX), manifest_id),
            CONVERT(VARBINARY(MAX), component_role),
            CONVERT(VARBINARY(MAX), variant_code),
            CONVERT(VARBINARY(MAX), run_signature_sha256),
            CONVERT(VARBINARY(MAX), run_status),
            CONVERT(VARBINARY(MAX), invariant_status),
            CONVERT(VARBINARY(MAX), invariant_evidence_sha256),
            CONVERT(VARBINARY(MAX), invariant_evidence_json),
            CONVERT(VARBINARY(MAX), model_frame_sha256),
            CONVERT(VARBINARY(MAX), fit_configuration_json),
            CONVERT(VARBINARY(MAX), result_evidence_sha256),
            started_ts,
            completed_ts,
            CONVERT(VARBINARY(MAX), created_by)
        FROM inserted
    )
    BEGIN
        THROW 51023, 'Monitoring evidence is immutable; sealing cannot alter observation fields.', 1;
    END;
END;
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_TERM_INSERT_GUARD
ON mlops.MODEL_MONITOR_TERM
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    -- Hold the parent lock through commit so a concurrent seal cannot admit late children.
    IF EXISTS (
        SELECT 1
        FROM inserted AS evidence
        WHERE NOT EXISTS (
            SELECT 1
            FROM mlops.MODEL_MONITOR_RUN AS monitor_run WITH (UPDLOCK, HOLDLOCK)
            WHERE monitor_run.monitor_run_id = evidence.monitor_run_id
              AND monitor_run.evidence_sealed = 0
        )
    )
    BEGIN
        THROW 51043, 'Monitoring evidence is sealed or its parent is missing.', 1;
    END;
END;
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_LAMBDA_INSERT_GUARD
ON mlops.MODEL_MONITOR_LAMBDA
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    -- Hold the parent lock through commit so a concurrent seal cannot admit late children.
    IF EXISTS (
        SELECT 1
        FROM inserted AS evidence
        WHERE NOT EXISTS (
            SELECT 1
            FROM mlops.MODEL_MONITOR_RUN AS monitor_run WITH (UPDLOCK, HOLDLOCK)
            WHERE monitor_run.monitor_run_id = evidence.monitor_run_id
              AND monitor_run.evidence_sealed = 0
        )
    )
    BEGIN
        THROW 51043, 'Monitoring evidence is sealed or its parent is missing.', 1;
    END;
END;
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_RELATIVITY_INSERT_GUARD
ON mlops.MODEL_MONITOR_RELATIVITY
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    -- Hold the parent lock through commit so a concurrent seal cannot admit late children.
    IF EXISTS (
        SELECT 1
        FROM inserted AS evidence
        WHERE NOT EXISTS (
            SELECT 1
            FROM mlops.MODEL_MONITOR_RUN AS monitor_run WITH (UPDLOCK, HOLDLOCK)
            WHERE monitor_run.monitor_run_id = evidence.monitor_run_id
              AND monitor_run.evidence_sealed = 0
        )
    )
    BEGIN
        THROW 51043, 'Monitoring evidence is sealed or its parent is missing.', 1;
    END;
END;
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_METRIC_INSERT_GUARD
ON mlops.MODEL_MONITOR_METRIC
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    -- Hold the parent lock through commit so a concurrent seal cannot admit late children.
    IF EXISTS (
        SELECT 1
        FROM inserted AS evidence
        WHERE NOT EXISTS (
            SELECT 1
            FROM mlops.MODEL_MONITOR_RUN AS monitor_run WITH (UPDLOCK, HOLDLOCK)
            WHERE monitor_run.monitor_run_id = evidence.monitor_run_id
              AND monitor_run.evidence_sealed = 0
        )
    )
    BEGIN
        THROW 51043, 'Monitoring evidence is sealed or its parent is missing.', 1;
    END;
END;
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
  ON manifest.manifest_id = monitor_run.manifest_id
WHERE monitor_run.evidence_sealed = 1;
GO

EXEC sys.sp_addextendedproperty
    @name = N'MS_Description',
    @value = N'Writers set 0, insert child evidence, then set 1 in one transaction. Sealed observations reject new children and cannot reopen. Existing rows default to 1 without certifying historical evidence.',
    @level0type = N'SCHEMA', @level0name = N'mlops',
    @level1type = N'TABLE', @level1name = N'MODEL_MONITOR_RUN',
    @level2type = N'COLUMN', @level2name = N'evidence_sealed';
GO

EXEC sys.sp_updateextendedproperty
    @name = N'MS_Description',
    @value = N'Purpose: Record a controlled scoring or refitting observation against a deployed baseline.
One row: One deployment, dataset snapshot, component, and monitoring variant.
Use: Writers insert child evidence before sealing the observation in the same transaction. Sealed evidence is immutable. Historical rows are closed without certifying their contents.',
    @level0type = N'SCHEMA', @level0name = N'mlops',
    @level1type = N'TABLE', @level1name = N'MODEL_MONITOR_RUN';
GO

EXEC sys.sp_updateextendedproperty
    @name = N'MS_Description',
    @value = N'Purpose: Compare monitoring observations with their deployed baseline and dated dataset.
One row: One sealed monitoring observation for a component and variant.
Use: Includes historical baseline deployments, status, and stored evidence digests. These observations are not candidate packages.',
    @level0type = N'SCHEMA', @level0name = N'pricing',
    @level1type = N'VIEW', @level1name = N'V_MODEL_MONITORING_RUN';
GO
