CREATE TABLE mlops.MODEL_MONITOR_PUBLICATION (
    monitor_run_id UNIQUEIDENTIFIER NOT NULL,
    model_run_id BIGINT NOT NULL,
    created_ts DATETIME2(3) NOT NULL CONSTRAINT DF_MODEL_MONITOR_PUBLICATION_CREATED_TS DEFAULT SYSUTCDATETIME(),
    created_by NVARCHAR(255) NOT NULL,
    CONSTRAINT PK_MODEL_MONITOR_PUBLICATION PRIMARY KEY (monitor_run_id),
    CONSTRAINT UQ_MODEL_MONITOR_PUBLICATION_RUN UNIQUE (model_run_id),
    CONSTRAINT FK_MODEL_MONITOR_PUBLICATION_MONITOR FOREIGN KEY (monitor_run_id) REFERENCES mlops.MODEL_MONITOR_RUN(monitor_run_id),
    CONSTRAINT FK_MODEL_MONITOR_PUBLICATION_RUN FOREIGN KEY (model_run_id) REFERENCES pricing.MODEL_RUN(model_run_id)
);
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_PUBLICATION_LINEAGE_GUARD
ON mlops.MODEL_MONITOR_PUBLICATION AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1 FROM inserted AS link
        WHERE NOT EXISTS (
            SELECT 1 FROM mlops.MODEL_MONITOR_RUN AS observation
            JOIN mlops.MODEL_FIT_CONTRACT AS contract ON contract.fit_contract_id=observation.fit_contract_id
            JOIN pricing.MODEL_RUN AS candidate ON candidate.model_run_id=link.model_run_id
            JOIN pricing.PRICING_RATE_PACKAGE AS package ON package.rate_package_id=candidate.rate_package_id
            JOIN pricing.MODEL_MONITORING_BASELINE AS snapshot ON snapshot.model_run_id=candidate.model_run_id
            WHERE observation.monitor_run_id=link.monitor_run_id
              AND observation.evidence_sealed=1 AND observation.run_status='SUCCESS'
              AND observation.invariant_status='VERIFIED'
              AND observation.variant_code IN ('FROZEN_REFIT','REESTIMATE_LAMBDA','FULL_ADAPTIVE')
              AND candidate.model_id=observation.model_id AND candidate.manifest_id=observation.manifest_id
              AND candidate.model_run_id<>contract.baseline_model_run_id
              AND candidate.run_status='SUCCESS' AND package.package_status='PUBLISHED'
              AND snapshot.capture_status='CAPTURED'
        )
    ) THROW 51050, 'Monitoring publication requires a matching sealed refit and captured candidate.', 1;
END;
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_PUBLICATION_IMMUTABLE
ON mlops.MODEL_MONITOR_PUBLICATION AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    THROW 51051, 'Monitoring publication links are immutable.', 1;
END;
GO

CREATE OR ALTER VIEW pricing.V_MODEL_CHALLENGER
AS
SELECT link.monitor_run_id, candidate.model_run_id, candidate.model_id, model.model_name,
       candidate.model_version, candidate.rate_package_id, package.package_version, package.package_status,
       observation.variant_code, data.data_as_of_date,
       baseline_data.data_as_of_date AS baseline_data_as_of_date,
       contract.baseline_model_run_id, observation.rate_package_id AS baseline_rate_package_id,
       observation.baseline_deployment_id, baseline_deployment.deployment_slot,
       current_deployment.deployment_id AS current_deployment_id,
       current_deployment.rate_package_id AS current_rate_package_id,
       CASE WHEN current_deployment.rate_package_id=candidate.rate_package_id THEN 1 ELSE 0 END AS is_current_champion,
       link.created_ts, link.created_by
FROM mlops.MODEL_MONITOR_PUBLICATION AS link
JOIN pricing.MODEL_RUN AS candidate ON candidate.model_run_id=link.model_run_id
JOIN pricing.PRICING_MODEL AS model ON model.model_id=candidate.model_id
JOIN pricing.PRICING_RATE_PACKAGE AS package ON package.rate_package_id=candidate.rate_package_id
JOIN pricing.DATASET_MANIFEST AS data ON data.manifest_id=candidate.manifest_id
JOIN mlops.MODEL_MONITOR_RUN AS observation ON observation.monitor_run_id=link.monitor_run_id
JOIN mlops.MODEL_FIT_CONTRACT AS contract ON contract.fit_contract_id=observation.fit_contract_id
JOIN pricing.MODEL_RUN AS baseline ON baseline.model_run_id=contract.baseline_model_run_id
JOIN pricing.DATASET_MANIFEST AS baseline_data ON baseline_data.manifest_id=baseline.manifest_id
JOIN pricing.PRICING_MODEL_DEPLOYMENT AS baseline_deployment ON baseline_deployment.deployment_id=observation.baseline_deployment_id
LEFT JOIN pricing.PRICING_MODEL_DEPLOYMENT AS current_deployment
  ON current_deployment.model_id=candidate.model_id
 AND current_deployment.deployment_slot=baseline_deployment.deployment_slot
 AND current_deployment.effective_to_ts IS NULL;
GO

CREATE OR ALTER TRIGGER pricing.TR_DATASET_MANIFEST_CHALLENGER_IDENTITY
ON pricing.DATASET_MANIFEST AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1 FROM deleted AS historical
        JOIN pricing.MODEL_RUN AS baseline ON baseline.manifest_id=historical.manifest_id
        JOIN mlops.MODEL_FIT_CONTRACT AS contract ON contract.baseline_model_run_id=baseline.model_run_id
        JOIN mlops.MODEL_MONITOR_RUN AS observation ON observation.fit_contract_id=contract.fit_contract_id
        JOIN mlops.MODEL_MONITOR_PUBLICATION AS publication ON publication.monitor_run_id=observation.monitor_run_id
    ) THROW 51053, 'Baseline dataset manifests referenced by challengers are immutable.', 1;
END;
GO

EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'One immutable published challenger per sealed monitoring refit. Publication does not deploy the package.',
    @level0type=N'SCHEMA', @level0name=N'mlops', @level1type=N'TABLE', @level1name=N'MODEL_MONITOR_PUBLICATION';
GO

EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Published monitoring challengers with their refit variant, candidate and baseline data dates, source lineage, and current champion identity. Use this view to compare selectable packages before explicit promotion.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'VIEW', @level1name=N'V_MODEL_CHALLENGER';
GO
