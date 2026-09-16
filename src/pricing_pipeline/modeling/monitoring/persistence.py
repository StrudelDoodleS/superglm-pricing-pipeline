"""Save a verified monitoring observation and recover identical concurrent retries.

Keep baseline lineage checks and SQL writes in one transaction. This consumes
MonitoringFitResult and returns PersistedMonitoringRun without fitting a model."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.monitoring.contracts import (
    FIT_CONTRACT_SCHEMA_VERSION,
    MonitoringError,
    MonitoringFitResult,
    MonitoringVariant,
    PersistedMonitoringRun,
    _canonical_json,
    _sha256_text,
)
from pricing_pipeline.modeling.monitoring.invariants import (
    _validate_persistable_invariant_evidence,
    _validate_persistable_result_evidence,
)
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
)


def _run_signature(
    *,
    baseline_deployment_id: int,
    manifest_id: str,
    variant: MonitoringVariant,
    contract_sha256: str,
    component_role: str,
    result_evidence_sha256: str,
) -> str:
    return _sha256_text(
        _canonical_json(
            {
                "baseline_deployment_id": int(baseline_deployment_id),
                "manifest_id": manifest_id,
                "variant": variant.value,
                "contract_sha256": contract_sha256,
                "component_role": component_role,
                "result_evidence_sha256": result_evidence_sha256,
            }
        )
    )


def _persist_monitoring_fit_once(
    engine,
    result: MonitoringFitResult,
    *,
    baseline_model_run_id: str | int,
    baseline_deployment_id: int,
    manifest_id: str,
    created_by: str,
    component_role: str = "OTHER",
) -> PersistedMonitoringRun:
    """Persist one completed observation, deduplicating an exact retry.

    SQLite stores the local mirror in ``pricing`` so persistent views remain
    usable when ``pricing.sqlite`` is opened directly.  SQL Server stores the
    same logical tables under ``mlops``.
    """
    invariant_evidence = _validate_persistable_invariant_evidence(result)
    result_evidence_sha256, baseline_identity = _validate_persistable_result_evidence(result)
    if not (
        isinstance(baseline_model_run_id, int)
        and not isinstance(baseline_model_run_id, bool)
        and baseline_model_run_id > 0
    ) and not (isinstance(baseline_model_run_id, str) and baseline_model_run_id.strip()):
        raise ValueError("baseline_model_run_id is required")
    for value, label in (
        (manifest_id, "manifest_id"),
        (created_by, "created_by"),
        (component_role, "component_role"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    component = component_role.strip().upper()
    if component not in {"FREQUENCY", "SEVERITY", "OTHER"}:
        raise ValueError("component_role must be FREQUENCY, SEVERITY, or OTHER")
    if str(baseline_identity["model_run_id"]) != str(baseline_model_run_id):
        raise MonitoringError("baseline_model_run_id does not match the verified candidate")
    if int(baseline_identity["deployment_id"]) != int(baseline_deployment_id):
        raise MonitoringError("baseline_deployment_id does not match the verified candidate")

    schemas = schema_names_from_connectable(engine)
    pricing_schema = schemas.pricing
    monitor_schema = pricing_schema if engine.dialect.name == "sqlite" else schemas.mlops
    signature = _run_signature(
        baseline_deployment_id=baseline_deployment_id,
        manifest_id=manifest_id,
        variant=result.variant,
        contract_sha256=result.contract.contract_sha256,
        component_role=component,
        result_evidence_sha256=result_evidence_sha256,
    )

    with engine.begin() as connection:
        if "snapshot_sha256" in baseline_identity:
            from pricing_pipeline.modeling.monitoring.storage import (
                verify_monitoring_snapshot_identity,
            )

            verify_monitoring_snapshot_identity(
                connection,
                model_run_id=baseline_model_run_id,
                snapshot_sha256=baseline_identity["snapshot_sha256"],
            )
        baseline = (
            connection.execute(
                text(
                    f"""
                    SELECT
                        mr.model_id,
                        mr.rate_package_id,
                        mr.model_version,
                        mr.export_id,
                        mr.manifest_id AS baseline_manifest_id,
                        mr.candidate_artifact_format,
                        mr.candidate_artifact_sha256,
                        mr.candidate_artifact_size_bytes,
                        mr.candidate_python_version,
                        mr.candidate_superglm_version,
                        mr.model_equivalence_sha256,
                        mr.model_source_sha256,
                        mr.publication_receipt_sha256,
                        rp.package_version,
                        rp.publication_receipt_sha256
                            AS package_publication_receipt_sha256,
                        baseline_manifest.model_frame_sha256 AS baseline_model_frame_sha256,
                        baseline_manifest.data_as_of_date AS baseline_data_as_of_date
                    FROM {pricing_schema}.MODEL_RUN AS mr
                    JOIN {pricing_schema}.PRICING_RATE_PACKAGE AS rp
                      ON rp.rate_package_id = mr.rate_package_id
                    JOIN {pricing_schema}.DATASET_MANIFEST AS baseline_manifest
                      ON baseline_manifest.manifest_id = mr.manifest_id
                    WHERE mr.model_run_id = :model_run_id
                      AND mr.run_status = 'SUCCESS'
                      AND rp.package_status = 'PUBLISHED'
                    """
                ),
                {"model_run_id": baseline_model_run_id},
            )
            .mappings()
            .one_or_none()
        )
        if baseline is None:
            raise MonitoringError(
                "baseline_model_run_id must identify a successful published model run"
            )
        expected_baseline = {
            "candidate_artifact_format": baseline["candidate_artifact_format"],
            "candidate_artifact_sha256": baseline["candidate_artifact_sha256"],
            "candidate_artifact_size_bytes": baseline["candidate_artifact_size_bytes"],
            "candidate_python_version": baseline["candidate_python_version"],
            "candidate_superglm_version": baseline["candidate_superglm_version"],
            "data_as_of_date": baseline["baseline_data_as_of_date"],
            "export_id": baseline["export_id"],
            "manifest_id": baseline["baseline_manifest_id"],
            "model_equivalence_sha256": baseline["model_equivalence_sha256"],
            "model_frame_sha256": baseline["baseline_model_frame_sha256"],
            "model_id": baseline["model_id"],
            "model_run_id": baseline_model_run_id,
            "model_source_sha256": baseline["model_source_sha256"],
            "model_version": baseline["model_version"],
            "package_version": baseline["package_version"],
            "package_publication_receipt_sha256": baseline["package_publication_receipt_sha256"],
            "publication_receipt_sha256": baseline["publication_receipt_sha256"],
            "rate_package_id": baseline["rate_package_id"],
        }
        mismatches = [
            field_name
            for field_name, expected in expected_baseline.items()
            if str(baseline_identity.get(field_name)) != str(expected)
        ]
        if mismatches:
            raise MonitoringError(
                "verified baseline candidate does not match SQL lineage: " + ", ".join(mismatches)
            )
        split_rows = (
            connection.execute(
                text(
                    f"""
                    SELECT split_set_id
                    FROM {schemas.mlops}.MODEL_RUN_SPLIT_SET
                    WHERE model_run_id = :model_run_id
                      AND manifest_id = :manifest_id
                      AND dataset_role = 'training'
                      AND split_role = 'validation'
                    """
                ),
                {
                    "model_run_id": baseline_model_run_id,
                    "manifest_id": baseline["baseline_manifest_id"],
                },
            )
            .scalars()
            .all()
        )
        if len(split_rows) > 1:
            raise MonitoringError(
                "baseline_model_run_id has ambiguous training/validation split lineage"
            )
        sql_split_set_id = None if not split_rows else str(split_rows[0])
        if baseline_identity.get("split_set_id") != sql_split_set_id:
            raise MonitoringError(
                "verified baseline candidate does not match SQL lineage: split_set_id"
            )
        # Keep the active deployment fixed until the evidence transaction commits.
        deployment_lock = " WITH (UPDLOCK, HOLDLOCK)" if engine.dialect.name == "mssql" else ""
        deployment = (
            connection.execute(
                text(
                    f"""
                    SELECT deployment_id, deployment_slot
                    FROM {pricing_schema}.PRICING_MODEL_DEPLOYMENT{deployment_lock}
                    WHERE deployment_id = :deployment_id
                      AND model_id = :model_id
                      AND rate_package_id = :rate_package_id
                      AND effective_to_ts IS NULL
                    """
                ),
                {
                    "deployment_id": int(baseline_deployment_id),
                    "model_id": baseline["model_id"],
                    "rate_package_id": baseline["rate_package_id"],
                },
            )
            .mappings()
            .one_or_none()
        )
        if deployment is None:
            raise MonitoringError(
                "baseline_deployment_id does not identify the supplied published model run"
            )
        if str(deployment["deployment_slot"]) != str(baseline_identity.get("deployment_slot")):
            raise MonitoringError(
                "verified baseline candidate does not match SQL lineage: deployment_slot"
            )
        manifest = (
            connection.execute(
                text(
                    f"""
                    SELECT
                        model_frame_sha256,
                        row_count,
                        target_column,
                        weight_column,
                        offset_column,
                        offset_source_column,
                        offset_label,
                        export_weight_column
                    FROM {pricing_schema}.DATASET_MANIFEST
                    WHERE manifest_id = :manifest_id
                    """
                ),
                {"manifest_id": manifest_id},
            )
            .mappings()
            .one_or_none()
        )
        if manifest is None:
            raise MonitoringError("manifest_id does not exist")
        if manifest["model_frame_sha256"] != result.model_frame_sha256:
            raise MonitoringError("monitoring model frame does not match manifest_id")
        if int(manifest["row_count"]) != int(result.metrics.get("row_count", -1)):
            raise MonitoringError("monitoring row count does not match manifest_id")
        fit_configuration = json.loads(result.fit_configuration_json)
        if manifest["target_column"] != fit_configuration.get("target_column"):
            raise MonitoringError("monitoring target column does not match manifest_id")
        try:
            offset_contract = OffsetExportContract.model_validate(
                fit_configuration["offset_contract"]
            )
            contract_model_metadata = result.contract.payload()["structure"]["package_metadata"][
                "model"
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise MonitoringError("monitoring fit/export role contract is malformed") from exc
        expected_manifest_roles = {
            "weight_column": fit_configuration.get("fit_sample_weight_name"),
            "offset_column": fit_configuration.get("offset_column"),
            "offset_source_column": (
                offset_contract.source_name
                if offset_contract.handling == "EXPORTED_FACTOR"
                else None
            ),
            "offset_label": offset_contract.label,
            "export_weight_column": contract_model_metadata.get("export_weight_name"),
        }
        for field_name, expected in expected_manifest_roles.items():
            if manifest[field_name] != expected:
                raise MonitoringError(f"monitoring {field_name} does not match manifest_id")

        existing_contract = (
            connection.execute(
                text(
                    f"""
                    SELECT fit_contract_id, contract_sha256
                    FROM {monitor_schema}.MODEL_FIT_CONTRACT
                    WHERE baseline_model_run_id = :model_run_id
                    """
                ),
                {"model_run_id": baseline_model_run_id},
            )
            .mappings()
            .one_or_none()
        )
        if existing_contract is None:
            fit_contract_id = str(uuid.uuid4())
            connection.execute(
                text(
                    f"""
                    INSERT INTO {monitor_schema}.MODEL_FIT_CONTRACT (
                        fit_contract_id, baseline_model_run_id, model_id,
                        rate_package_id, contract_schema_version,
                        contract_sha256, structure_sha256, contract_json,
                        superglm_version, created_by
                    ) VALUES (
                        :fit_contract_id, :baseline_model_run_id, :model_id,
                        :rate_package_id, :schema_version,
                        :contract_sha256, :structure_sha256, :contract_json,
                        :superglm_version, :created_by
                    )
                    """
                ),
                {
                    "fit_contract_id": fit_contract_id,
                    "baseline_model_run_id": baseline_model_run_id,
                    "model_id": baseline["model_id"],
                    "rate_package_id": baseline["rate_package_id"],
                    "schema_version": FIT_CONTRACT_SCHEMA_VERSION,
                    "contract_sha256": result.contract.contract_sha256,
                    "structure_sha256": result.contract.structure_sha256,
                    "contract_json": result.contract.contract_json,
                    "superglm_version": result.contract.superglm_version,
                    "created_by": created_by.strip(),
                },
            )
        else:
            fit_contract_id = str(existing_contract["fit_contract_id"])
            if existing_contract["contract_sha256"] != result.contract.contract_sha256:
                raise MonitoringError(
                    "the immutable fit contract for baseline_model_run_id has changed; "
                    "publish/deploy a new baseline rather than mutating its contract"
                )

        existing_run = (
            connection.execute(
                text(
                    f"""
                    SELECT monitor_run_id, run_signature_sha256, evidence_sealed
                    FROM {monitor_schema}.MODEL_MONITOR_RUN
                    WHERE baseline_deployment_id = :baseline_deployment_id
                      AND manifest_id = :manifest_id
                      AND component_role = :component_role
                      AND variant_code = :variant_code
                    """
                ),
                {
                    "baseline_deployment_id": int(baseline_deployment_id),
                    "manifest_id": manifest_id,
                    "component_role": component,
                    "variant_code": result.variant.value,
                },
            )
            .mappings()
            .one_or_none()
        )
        if existing_run is not None:
            if not existing_run["evidence_sealed"]:
                raise MonitoringError(
                    "a monitoring observation already exists with unsealed evidence"
                )
            if existing_run["run_signature_sha256"] != signature:
                raise MonitoringError(
                    "a monitoring observation already exists with different fit evidence"
                )
            return PersistedMonitoringRun(
                monitor_run_id=str(existing_run["monitor_run_id"]),
                fit_contract_id=fit_contract_id,
                run_signature_sha256=signature,
                deduplicated=True,
            )

        monitor_run_id = str(uuid.uuid4())
        connection.execute(
            text(
                f"""
                INSERT INTO {monitor_schema}.MODEL_MONITOR_RUN (
                    monitor_run_id, fit_contract_id, baseline_deployment_id,
                    model_id, rate_package_id, manifest_id, component_role,
                    variant_code, run_signature_sha256, run_status,
                    invariant_status, invariant_evidence_sha256,
                    invariant_evidence_json, model_frame_sha256,
                    fit_configuration_json, result_evidence_sha256,
                    created_by, evidence_sealed
                ) VALUES (
                    :monitor_run_id, :fit_contract_id, :baseline_deployment_id,
                    :model_id, :rate_package_id, :manifest_id, :component_role,
                    :variant_code, :signature, 'SUCCESS',
                    :invariant_status, :invariant_evidence_sha256,
                    :invariant_evidence_json, :model_frame_sha256,
                    :fit_configuration_json, :result_evidence_sha256,
                    :created_by, 0
                )
                """
            ),
            {
                "monitor_run_id": monitor_run_id,
                "fit_contract_id": fit_contract_id,
                "baseline_deployment_id": int(baseline_deployment_id),
                "model_id": baseline["model_id"],
                "rate_package_id": baseline["rate_package_id"],
                "manifest_id": manifest_id,
                "component_role": component,
                "variant_code": result.variant.value,
                "signature": signature,
                "invariant_status": invariant_evidence.status,
                "invariant_evidence_sha256": invariant_evidence.evidence_sha256,
                "invariant_evidence_json": invariant_evidence.evidence_json,
                "model_frame_sha256": result.model_frame_sha256,
                "fit_configuration_json": result.fit_configuration_json,
                "result_evidence_sha256": result_evidence_sha256,
                "created_by": created_by.strip(),
            },
        )
        if result.terms:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {monitor_schema}.MODEL_MONITOR_TERM (
                        monitor_run_id, term_name, term_kind, sequence_no,
                        term_structure_sha256, term_metadata_json
                    ) VALUES (
                        :monitor_run_id, :term_name, :term_kind, :sequence_no,
                        :structure_sha256, :metadata_json
                    )
                    """
                ),
                [
                    {
                        "monitor_run_id": monitor_run_id,
                        "term_name": row.term_name,
                        "term_kind": row.term_kind,
                        "sequence_no": row.sequence_no,
                        "structure_sha256": row.structure_sha256,
                        "metadata_json": row.metadata_json,
                    }
                    for row in result.terms
                ],
            )
        if result.lambdas:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {monitor_schema}.MODEL_MONITOR_LAMBDA (
                        monitor_run_id, component_name, term_name,
                        lambda_value, lambda_mode
                    ) VALUES (
                        :monitor_run_id, :component_name, :term_name,
                        :lambda_value, :lambda_mode
                    )
                    """
                ),
                [
                    {
                        "monitor_run_id": monitor_run_id,
                        "component_name": row.component_name,
                        "term_name": row.term_name,
                        "lambda_value": row.lambda_value,
                        "lambda_mode": row.lambda_mode,
                    }
                    for row in result.lambdas
                ],
            )
        if result.relativities:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {monitor_schema}.MODEL_MONITOR_RELATIVITY (
                        monitor_run_id, term_name, term_kind, point_key,
                        point_label, point_numeric, relativity,
                        log_relativity, is_reference
                    ) VALUES (
                        :monitor_run_id, :term_name, :term_kind, :point_key,
                        :point_label, :point_numeric, :relativity,
                        :log_relativity, :is_reference
                    )
                    """
                ),
                [
                    {
                        "monitor_run_id": monitor_run_id,
                        "term_name": row.term_name,
                        "term_kind": row.term_kind,
                        "point_key": row.point_key,
                        "point_label": row.point_label,
                        "point_numeric": row.point_numeric,
                        "relativity": row.relativity,
                        "log_relativity": row.log_relativity,
                        "is_reference": int(row.is_reference),
                    }
                    for row in result.relativities
                ],
            )
        if result.metrics:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {monitor_schema}.MODEL_MONITOR_METRIC (
                        monitor_run_id, metric_name, metric_value
                    ) VALUES (
                        :monitor_run_id, :metric_name, :metric_value
                    )
                    """
                ),
                [
                    {
                        "monitor_run_id": monitor_run_id,
                        "metric_name": name,
                        "metric_value": value,
                    }
                    for name, value in result.metrics.items()
                ],
            )

        connection.execute(
            text(
                f"UPDATE {monitor_schema}.MODEL_MONITOR_RUN "
                "SET evidence_sealed = 1 WHERE monitor_run_id = :monitor_run_id "
                "AND evidence_sealed = 0"
            ),
            {"monitor_run_id": monitor_run_id},
        )

    return PersistedMonitoringRun(
        monitor_run_id=monitor_run_id,
        fit_contract_id=fit_contract_id,
        run_signature_sha256=signature,
        deduplicated=False,
    )


def _recover_concurrent_monitoring_retry(
    engine,
    result: MonitoringFitResult,
    *,
    baseline_deployment_id: int,
    manifest_id: str,
    component_role: str,
) -> PersistedMonitoringRun | None:
    result_evidence_sha256, _ = _validate_persistable_result_evidence(result)
    component = component_role.strip().upper()
    signature = _run_signature(
        baseline_deployment_id=baseline_deployment_id,
        manifest_id=manifest_id,
        variant=result.variant,
        contract_sha256=result.contract.contract_sha256,
        component_role=component,
        result_evidence_sha256=result_evidence_sha256,
    )
    schemas = schema_names_from_connectable(engine)
    monitor_schema = schemas.pricing if engine.dialect.name == "sqlite" else schemas.mlops
    with engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    f"""
                    SELECT
                        monitor_run_id,
                        fit_contract_id,
                        run_signature_sha256,
                        evidence_sealed
                    FROM {monitor_schema}.MODEL_MONITOR_RUN
                    WHERE baseline_deployment_id = :baseline_deployment_id
                      AND manifest_id = :manifest_id
                      AND component_role = :component_role
                      AND variant_code = :variant_code
                    """
                ),
                {
                    "baseline_deployment_id": int(baseline_deployment_id),
                    "manifest_id": manifest_id,
                    "component_role": component,
                    "variant_code": result.variant.value,
                },
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    if not row["evidence_sealed"]:
        raise MonitoringError("a concurrent monitoring observation has unsealed evidence")
    if row["run_signature_sha256"] != signature:
        raise MonitoringError(
            "a concurrent monitoring observation committed different fit evidence"
        )
    return PersistedMonitoringRun(
        monitor_run_id=str(row["monitor_run_id"]),
        fit_contract_id=str(row["fit_contract_id"]),
        run_signature_sha256=signature,
        deduplicated=True,
    )


def persist_monitoring_fit(
    engine,
    result: MonitoringFitResult,
    *,
    baseline_model_run_id: str | int,
    baseline_deployment_id: int,
    manifest_id: str,
    created_by: str,
    component_role: str = "OTHER",
) -> PersistedMonitoringRun:
    """Verify and save a monitoring result against its baseline and dataset.

    Write the contract, metrics and relativity evidence in the audit database.
    Reuse an identical observation on retry and return ``PersistedMonitoringRun``.
    """
    try:
        return _persist_monitoring_fit_once(
            engine,
            result,
            baseline_model_run_id=baseline_model_run_id,
            baseline_deployment_id=baseline_deployment_id,
            manifest_id=manifest_id,
            created_by=created_by,
            component_role=component_role,
        )
    except (IntegrityError, OperationalError):  # fmt: skip
        recovered = _recover_concurrent_monitoring_retry(
            engine,
            result,
            baseline_deployment_id=baseline_deployment_id,
            manifest_id=manifest_id,
            component_role=component_role,
        )
        if recovered is None:
            raise
        return recovered
