-- A nullable legacy MODEL_RUN identity must not pass a monitoring lineage check.
CREATE OR ALTER TRIGGER mlops.TR_MODEL_FIT_CONTRACT_LINEAGE_GUARD
ON mlops.MODEL_FIT_CONTRACT
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted AS contract
        WHERE NOT EXISTS (
            SELECT 1
            FROM pricing.MODEL_RUN AS baseline_run
            JOIN pricing.PRICING_RATE_PACKAGE AS package
              ON package.rate_package_id = contract.rate_package_id
            WHERE baseline_run.model_run_id = contract.baseline_model_run_id
              AND baseline_run.model_id = contract.model_id
              AND baseline_run.rate_package_id = contract.rate_package_id
              AND baseline_run.run_status = 'SUCCESS'
              AND package.model_id = contract.model_id
              AND package.package_status = 'PUBLISHED'
        )
    )
    BEGIN
        THROW 51022, 'A fit contract must identify one successful published baseline run.', 1;
    END;
END;
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_RUN_LINEAGE_GUARD
ON mlops.MODEL_MONITOR_RUN
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted AS monitor_run
        WHERE NOT EXISTS (
            SELECT 1
            FROM mlops.MODEL_FIT_CONTRACT AS contract
            JOIN pricing.MODEL_RUN AS baseline_run
              ON baseline_run.model_run_id = contract.baseline_model_run_id
            JOIN pricing.PRICING_MODEL_DEPLOYMENT AS deployment
              ON deployment.deployment_id = monitor_run.baseline_deployment_id
            WHERE contract.fit_contract_id = monitor_run.fit_contract_id
              AND contract.model_id = monitor_run.model_id
              AND contract.rate_package_id = monitor_run.rate_package_id
              AND baseline_run.model_id = monitor_run.model_id
              AND baseline_run.rate_package_id = monitor_run.rate_package_id
              AND baseline_run.run_status = 'SUCCESS'
              AND deployment.model_id = monitor_run.model_id
              AND deployment.rate_package_id = monitor_run.rate_package_id
        )
    )
    BEGIN
        THROW 51021, 'Monitoring contract, baseline run, and deployment must identify one successful model package.', 1;
    END;
END;
GO

-- Protect the referenced side too; annotations on a run may still be corrected.
CREATE OR ALTER TRIGGER pricing.TR_MODEL_RUN_MONITORING_LINEAGE_GUARD
ON pricing.MODEL_RUN
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM deleted AS historical_run
        JOIN mlops.MODEL_FIT_CONTRACT AS contract
          ON contract.baseline_model_run_id = historical_run.model_run_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM inserted AS current_run
            WHERE current_run.model_run_id = historical_run.model_run_id
              AND current_run.model_id = historical_run.model_id
              AND current_run.rate_package_id = historical_run.rate_package_id
              AND current_run.run_status = historical_run.run_status
        )
    )
    BEGIN
        THROW 51028, 'A baseline run referenced by a fit contract retains its lineage identity.', 1;
    END;
END;
GO
