CREATE OR ALTER VIEW pricing.V_MODEL_REGISTRY
AS
WITH model_slots AS (
    SELECT DISTINCT model_id, deployment_slot FROM pricing.PRICING_MODEL_DEPLOYMENT
)
SELECT model.model_name, model.model_label, slots.deployment_slot,
       CASE WHEN current_deployment.rate_package_id=package.rate_package_id THEN 'CHAMPION'
            WHEN EXISTS (
                SELECT 1 FROM pricing.PRICING_MODEL_DEPLOYMENT AS history
                WHERE history.model_id=model.model_id
                  AND history.rate_package_id=package.rate_package_id
                  AND history.deployment_slot=slots.deployment_slot
                  AND history.effective_to_ts IS NOT NULL
            ) THEN 'FORMER_CHAMPION'
            ELSE 'CHALLENGER' END AS role,
       recipe.recipe_revision AS definition_revision,
       CASE observation.variant_code
           WHEN 'FROZEN_REFIT' THEN 'Coefficients only'
           WHEN 'REESTIMATE_LAMBDA' THEN 'Coefficients and smoothing'
           WHEN 'FULL_ADAPTIVE' THEN 'Full refit'
           ELSE CASE run.model_kind WHEN 'RAW' THEN 'Analyst fit'
                                   WHEN 'ROUTINE_EDIT' THEN 'Grouped fit'
                                   ELSE 'Manual adjustment' END
       END AS refit_type,
       manifest.data_as_of_date, package.created_ts AS published_at,
       package.package_version, package.rate_package_id, run.model_run_id,
       run.model_version AS fit_version, package.package_status, run.model_kind,
       model.model_id, model.target_name, model.model_type,
       run.recipe_status, recipe.recipe_sha256, run.manifest_id,
       observation.variant_code AS monitoring_variant, observation.monitor_run_id,
       contract.baseline_model_run_id,
       observation.rate_package_id AS baseline_rate_package_id,
       observation.baseline_deployment_id,
       baseline_manifest.data_as_of_date AS baseline_data_as_of_date,
       current_deployment.deployment_id AS current_deployment_id,
       current_deployment.rate_package_id AS current_rate_package_id,
       CASE WHEN current_deployment.rate_package_id=package.rate_package_id THEN 1 ELSE 0 END AS is_current_champion,
       run.created_by
FROM pricing.MODEL_RUN AS run
JOIN pricing.PRICING_MODEL AS model ON model.model_id=run.model_id
JOIN pricing.PRICING_RATE_PACKAGE AS package
  ON package.rate_package_id=run.rate_package_id AND package.model_id=run.model_id
JOIN pricing.DATASET_MANIFEST AS manifest ON manifest.manifest_id=run.manifest_id
LEFT JOIN pricing.MODEL_RECIPE AS recipe
  ON recipe.recipe_id=run.recipe_id AND recipe.model_id=run.model_id
LEFT JOIN mlops.MODEL_MONITOR_PUBLICATION AS publication ON publication.model_run_id=run.model_run_id
LEFT JOIN mlops.MODEL_MONITOR_RUN AS observation ON observation.monitor_run_id=publication.monitor_run_id
LEFT JOIN mlops.MODEL_FIT_CONTRACT AS contract ON contract.fit_contract_id=observation.fit_contract_id
LEFT JOIN pricing.MODEL_RUN AS baseline ON baseline.model_run_id=contract.baseline_model_run_id
LEFT JOIN pricing.DATASET_MANIFEST AS baseline_manifest ON baseline_manifest.manifest_id=baseline.manifest_id
LEFT JOIN pricing.PRICING_MODEL_DEPLOYMENT AS origin_deployment
  ON origin_deployment.deployment_id=observation.baseline_deployment_id
LEFT JOIN model_slots AS slots ON slots.model_id=model.model_id
  AND (publication.monitor_run_id IS NULL OR slots.deployment_slot=origin_deployment.deployment_slot)
LEFT JOIN pricing.PRICING_MODEL_DEPLOYMENT AS current_deployment
  ON current_deployment.model_id=model.model_id
 AND current_deployment.deployment_slot=slots.deployment_slot
 AND current_deployment.effective_to_ts IS NULL
WHERE run.run_status='SUCCESS' AND package.package_status='PUBLISHED'
  AND (publication.monitor_run_id IS NULL OR (
      observation.run_status='SUCCESS' AND observation.invariant_status='VERIFIED'
      AND observation.evidence_sealed=1));
GO

CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_PUBLICATION_RECIPE
ON mlops.MODEL_MONITOR_PUBLICATION AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1 FROM inserted AS link
        JOIN mlops.MODEL_MONITOR_RUN AS observation ON observation.monitor_run_id=link.monitor_run_id
        JOIN mlops.MODEL_FIT_CONTRACT AS contract ON contract.fit_contract_id=observation.fit_contract_id
        JOIN pricing.MODEL_RUN AS baseline ON baseline.model_run_id=contract.baseline_model_run_id
        JOIN pricing.MODEL_RUN AS candidate ON candidate.model_run_id=link.model_run_id
        WHERE candidate.recipe_status<>baseline.recipe_status
           OR ISNULL(candidate.recipe_id,-1)<>ISNULL(baseline.recipe_id,-1)
           OR ISNULL(candidate.recipe_unavailable_reason,'')<>ISNULL(baseline.recipe_unavailable_reason,'')
    ) THROW 51054, 'Monitoring challengers must retain their baseline model definition.', 1;
END;
GO

EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'One saved fit per model and known deployment slot, including the initial champion, challengers and former champions. Definition revision describes declared choices; package/run IDs identify fits. A never-deployed model has a NULL slot. Monitoring fits stay in their originating slot. Promotion is manual.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'VIEW', @level1name=N'V_MODEL_REGISTRY';
GO

EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Declared model recipe revision. Weekly refits inherit it. NULL means no captured recipe; inspect recipe_status. Temporary frozen knots/lambdas and learned coefficients do not allocate a revision.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'VIEW', @level1name=N'V_MODEL_REGISTRY',
    @level2type=N'COLUMN', @level2name=N'definition_revision';
GO

EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'Legacy model_version fit identifier retained for audit joins. This is not the declared model definition revision or a deployment sequence.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'VIEW', @level1name=N'V_MODEL_REGISTRY',
    @level2type=N'COLUMN', @level2name=N'fit_version';
GO

EXEC sys.sp_addextendedproperty @name=N'MS_Description',
    @value=N'UTC creation timestamp of the published PRICING_RATE_PACKAGE. Distinct from the source completeness date in data_as_of_date and the time a human deploys the package.',
    @level0type=N'SCHEMA', @level0name=N'pricing', @level1type=N'VIEW', @level1name=N'V_MODEL_REGISTRY',
    @level2type=N'COLUMN', @level2name=N'published_at';
GO
