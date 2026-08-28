"""Publish prepared rating tables in one explicit SQL Server transaction.

Concrete package SQL remains here; lineage writes live in ``lineage.py`` and run in
the same transaction so maintainers can audit order without a repository abstraction.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.publishing.identity import canonical_json, canonical_revision_metadata
from pricing_pipeline.publishing.lineage import record_model_run
from pricing_pipeline.publishing.metadata import SuperGLMPublicationReceipt
from pricing_pipeline.publishing.publish import (
    CompletedModelPublishResult,
    DraftVerification,
    ModelRegistryError,
    PreparedPublication,
    PricingModelRecord,
)
from pricing_pipeline.publishing.rating_tables import RatingTables
from pricing_pipeline.workbench.artifacts import CandidateBundle
from pricing_pipeline.workbench.submission import EditorSubmissionError, sha256_file

_VERSION_PATTERN = re.compile(r"^v([0-9]+)$")
_LOCK_TIMEOUT_MS = 10_000
_LOCK_RESOURCE_PREFIX = "pricing_staging_export:"


def get_pricing_model(connection, model_name: str) -> PricingModelRecord | None:
    row = (
        connection.execute(
            text(
                """
                SELECT model_id, model_name, model_label, target_name, model_type, model_status
                FROM pricing.PRICING_MODEL
                WHERE model_name = :model_name
                """
            ),
            {"model_name": model_name},
        )
        .mappings()
        .one_or_none()
    )
    return None if row is None else PricingModelRecord(**dict(row))


def validate_registered_model(connection, config: ModelBuildConfig) -> PricingModelRecord:
    record = get_pricing_model(connection, config.model_name)
    if record is None:
        raise ModelRegistryError(
            f"model_name {config.model_name!r} is not registered; "
            "run explicit model registration first"
        )
    mismatches = [
        f"{field} db={getattr(record, field)!r} config={expected!r}"
        for field, expected in (
            ("model_label", config.model_label),
            ("target_name", config.target_name),
            ("model_type", config.model_type),
        )
        if getattr(record, field) != expected
    ]
    if record.model_status != "ACTIVE":
        mismatches.append(f"model_status db={record.model_status!r} expected='ACTIVE'")
    if mismatches:
        raise ModelRegistryError(
            f"registered model {config.model_name!r} does not match config: "
            + "; ".join(mismatches)
        )
    return record


def register_pricing_model(
    connection,
    config: ModelBuildConfig,
    *,
    created_by: str,
) -> PricingModelRecord:
    connection.execute(
        text(
            """
            INSERT INTO pricing.PRICING_MODEL (
                model_name, model_label, target_name, model_type, model_status, created_by
            )
            SELECT :model_name, :model_label, :target_name, :model_type, 'ACTIVE', :created_by
            WHERE NOT EXISTS (
                SELECT 1 FROM pricing.PRICING_MODEL WITH (UPDLOCK, HOLDLOCK)
                WHERE model_name = :model_name
            );
            """
        ),
        {
            "model_name": config.model_name,
            "model_label": config.model_label,
            "target_name": config.target_name,
            "model_type": config.model_type,
            "created_by": created_by,
        },
    )
    return validate_registered_model(connection, config)


def _required_text(value: str, field_name: str) -> str:
    cleaned = "" if value is None else str(value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


def resolve_model_version_for_export(
    engine,
    *,
    model_name: str,
    export_id: str,
) -> str:
    model_name = _required_text(model_name, "model_name")
    export_id = _required_text(export_id, "export_id")
    schemas = schema_names_from_connectable(engine)
    with engine.begin() as connection:
        model_id = connection.execute(
            text(
                f"""
                SELECT pm.model_id
                FROM {schemas.pricing}.PRICING_MODEL AS pm WITH (UPDLOCK, HOLDLOCK)
                WHERE pm.model_name = :model_name
                """
            ),
            {"model_name": model_name},
        ).scalar_one_or_none()
        if model_id is None:
            raise ValueError(f"pricing model is not registered: {model_name}")
        params = {"model_id": int(model_id), "export_id": export_id}
        existing_versions = list(
            connection.execute(
                text(
                    f"""
                    SELECT existing.model_version
                    FROM (
                        SELECT rp.model_version
                        FROM {schemas.pricing}.PRICING_RATE_PACKAGE AS rp
                        WHERE rp.model_id = :model_id AND rp.source_export_id = :export_id
                        UNION
                        SELECT reservation.model_version
                        FROM {schemas.pricing}.PRICING_MODEL_VERSION_RESERVATION AS reservation
                        WHERE reservation.model_id = :model_id
                          AND reservation.export_id = :export_id
                    ) AS existing
                    """
                ),
                params,
            ).scalars()
        )
        if len(existing_versions) > 1:
            raise RuntimeError(
                "published package and model-version reservation disagree for "
                f"model={model_name!r}, export_id={export_id!r}"
            )
        if existing_versions:
            return str(existing_versions[0])
        versions = connection.execute(
            text(
                f"""
                SELECT rp.model_version
                FROM {schemas.pricing}.PRICING_RATE_PACKAGE AS rp
                WHERE rp.model_id = :model_id AND rp.parent_rate_package_id IS NULL
                UNION ALL
                SELECT reservation.model_version
                FROM {schemas.pricing}.PRICING_MODEL_VERSION_RESERVATION AS reservation
                WHERE reservation.model_id = :model_id
                """
            ),
            params,
        ).scalars()
        numbers = [
            int(match.group(1))
            for value in versions
            if (match := _VERSION_PATTERN.match(str(value))) is not None
        ]
        reserved = f"v{max(numbers, default=0) + 1}"
        connection.execute(
            text(
                f"""
                INSERT INTO {schemas.pricing}.PRICING_MODEL_VERSION_RESERVATION (
                    model_id, export_id, model_version
                ) VALUES (:model_id, :export_id, :model_version)
                """
            ),
            {**params, "model_version": reserved},
        )
        return reserved


def _identity_text(value) -> str | None:
    if value is None:
        return None
    return str(value)


def _existing_export_conflicts(
    existing_package,
    meta,
    *,
    parent_rate_package_id: int | None,
    revision_metadata_json: str | None,
) -> list[str]:
    conflicts: list[str] = []
    for field_name in (
        "model_version",
        "effective_from_date",
        "effective_to_date",
        "source_file",
        "publication_receipt_sha256",
        "staging_content_sha256",
    ):
        existing_value = _identity_text(existing_package[field_name])
        staged_value = _identity_text(meta[field_name])
        if field_name == "source_file" and (existing_value is None or staged_value is None):
            continue
        if existing_value != staged_value:
            conflicts.append(
                f"{field_name} existing={existing_package[field_name]!r} "
                f"staged={meta[field_name]!r}"
            )
    requested_identity = {
        "parent_rate_package_id": parent_rate_package_id,
        "revision_metadata_json": revision_metadata_json,
    }
    for field_name, requested_value in requested_identity.items():
        existing_value = existing_package.get(field_name)
        if _identity_text(existing_value) != _identity_text(requested_value):
            conflicts.append(
                f"{field_name} existing={existing_value!r} requested={requested_value!r}"
            )
    return conflicts


def _delete_staging_children(
    connection: Connection,
    *,
    export_id: str,
) -> None:
    """Remove bulky staged children while retaining the retry/audit header."""
    params = {"export_id": export_id}
    for statement in (
        "DELETE FROM pricing_stg.STG_TERM_METADATA WHERE export_id = :export_id",
        "DELETE FROM pricing_stg.STG_CELL_LEVEL WHERE export_id = :export_id",
        "DELETE FROM pricing_stg.STG_RATE_CELL WHERE export_id = :export_id",
    ):
        connection.execute(text(statement), params)


@dataclass(frozen=True)
class _DraftPackage:
    rate_package_id: int
    package_version: int
    model_id: int
    export_id: str


def _lock_export(connection: Connection, export_id: str) -> None:
    dialect = getattr(connection, "dialect", None)
    if dialect is None:
        dialect = getattr(getattr(connection, "engine", None), "dialect", None)
    if getattr(dialect, "name", None) != "mssql":
        return
    export_id = _required_text(export_id, "export_id")
    result = connection.execute(
        text(
            """
            DECLARE @lock_result INT;
            EXEC @lock_result = sys.sp_getapplock
                @Resource = :lock_resource,
                @LockMode = 'Exclusive',
                @LockOwner = 'Transaction',
                @LockTimeout = :lock_timeout_ms;
            SELECT @lock_result;
            """
        ),
        {
            "lock_resource": f"{_LOCK_RESOURCE_PREFIX}{export_id}",
            "lock_timeout_ms": _LOCK_TIMEOUT_MS,
        },
    ).scalar_one()
    if int(result) < 0:
        raise RuntimeError(
            f"could not acquire staging publication lock for export_id={export_id!r}"
        )


def _prepared_staged_metadata(
    prepared: PreparedPublication,
    tables: RatingTables,
) -> dict[str, object]:
    return {
        "export_id": prepared.build.export_id,
        "model_id": prepared.build.model_id,
        "model_name": prepared.model_config.model_name,
        "model_version": prepared.build.model_version,
        "effective_from_date": prepared.build.effective_from,
        "effective_to_date": prepared.effective_to,
        "source_file": str(Path(prepared.build.rating_workbook_path).resolve()),
        "publication_receipt_sha256": prepared.build.publication_receipt_sha256,
        "staging_content_sha256": tables.staging_content_sha256,
        "model_equivalence_sha256": tables.model_equivalence_sha256,
    }


def _retry_evidence_conflicts(
    *,
    row: dict,
    prepared: PreparedPublication,
    dataset_rows: list[dict],
    split_rows: list[dict],
    metric_rows: list[dict],
    fold_rows: list[dict],
) -> list[str]:
    export = prepared.build
    expected_manifest_id = export.manifest_id
    expected_split_set_id = export.split_set_id
    path_fields = {
        "source_file",
        "rating_workbook_path",
        "publication_receipt_path",
        "candidate_artifact_path",
    }
    date_fields = {"effective_from_date", "effective_to_date"}
    integer_fields = {
        "model_id",
        "run_model_id",
        "parent_model_run_id",
        "candidate_artifact_size_bytes",
    }
    expected_scalars = {
        "model_id": export.model_id,
        "model_name": export.model_name,
        "model_version": export.model_version,
        "source_export_id": export.export_id,
        "parent_rate_package_id": prepared.parent_rate_package_id,
        "effective_from_date": export.effective_from,
        "effective_to_date": prepared.effective_to,
        "source_file": export.rating_workbook_path,
        "package_publication_receipt_sha256": export.publication_receipt_sha256,
        "run_export_id": export.export_id,
        "run_model_id": export.model_id,
        "run_model_name": export.model_name,
        "run_model_version": export.model_version,
        "parent_model_run_id": prepared.parent_model_run_id,
        "model_kind": export.model_kind,
        "model_equivalence_sha256": export.model_equivalence_sha256,
        "dag_id": prepared.execution_name,
        "airflow_run_id": prepared.execution_id,
        "mlflow_run_id": export.mlflow_run_id,
        "manifest_id": expected_manifest_id,
        "rating_workbook_path": export.rating_workbook_path,
        "rating_workbook_sha256": export.rating_workbook_sha256,
        "publication_receipt_path": export.publication_receipt_path,
        "publication_receipt_sha256": export.publication_receipt_sha256,
        "candidate_artifact_path": export.candidate_artifact_path,
        "candidate_artifact_sha256": export.candidate_artifact_sha256,
        "candidate_artifact_format": export.candidate_artifact_format,
        "candidate_artifact_size_bytes": export.candidate_artifact_size_bytes,
        "candidate_python_version": export.candidate_python_version,
        "candidate_superglm_version": export.candidate_superglm_version,
        "model_source_sha256": export.model_source_sha256,
    }
    conflicts: list[str] = []
    for field_name, expected_value in expected_scalars.items():
        actual_value = row.get(field_name)
        if field_name == "model_kind" and actual_value is None:
            actual_value = "RAW"
        if field_name in path_fields:
            expected_identity = (
                None
                if expected_value is None
                else str(Path(str(expected_value)).expanduser().resolve())
            )
            actual_identity = (
                None
                if actual_value is None
                else str(Path(str(actual_value)).expanduser().resolve())
            )
        elif field_name in date_fields:
            expected_isoformat = getattr(expected_value, "isoformat", None)
            actual_isoformat = getattr(actual_value, "isoformat", None)
            expected_identity = (
                None
                if expected_value is None
                else str(expected_isoformat() if callable(expected_isoformat) else expected_value)
            )
            actual_identity = (
                None
                if actual_value is None
                else str(actual_isoformat() if callable(actual_isoformat) else actual_value)
            )
        elif field_name in integer_fields:
            expected_identity = None if expected_value is None else int(expected_value)
            actual_identity = None if actual_value is None else int(actual_value)
        else:
            expected_identity = None if expected_value is None else str(expected_value)
            actual_identity = None if actual_value is None else str(actual_value)
        if actual_identity != expected_identity:
            conflicts.append(
                f"{field_name} expected={expected_identity!r} stored={actual_identity!r}"
            )

    expected_datasets = {(expected_manifest_id, "training")}
    actual_datasets = {
        (str(item["manifest_id"]), str(item["dataset_role"])) for item in dataset_rows
    }
    if actual_datasets != expected_datasets:
        conflicts.append(
            f"dataset links expected={sorted(expected_datasets)!r} "
            f"stored={sorted(actual_datasets)!r}"
        )

    expected_splits = (
        set()
        if expected_split_set_id is None
        else {
            (
                expected_manifest_id,
                expected_split_set_id,
                "training",
                "validation",
            )
        }
    )
    actual_splits = {
        (
            str(item["manifest_id"]),
            str(item["split_set_id"]),
            str(item["dataset_role"]),
            str(item["split_role"]),
        )
        for item in split_rows
    }
    if actual_splits != expected_splits:
        conflicts.append(
            f"split links expected={sorted(expected_splits)!r} stored={sorted(actual_splits)!r}"
        )

    expected_metrics = {
        str(name): (
            float(value),
            (None if export.metric_scopes.get(name) is None else str(export.metric_scopes[name])),
        )
        for name, value in export.metrics.items()
    }
    actual_metrics = {
        str(item["metric_name"]): (
            float(item["metric_value"]),
            None if item.get("metric_scope") is None else str(item["metric_scope"]),
        )
        for item in metric_rows
    }
    if actual_metrics != expected_metrics:
        conflicts.append(f"metrics expected={expected_metrics!r} stored={actual_metrics!r}")

    expected_folds = {
        (
            None if expected_split_set_id is None else str(expected_split_set_id),
            int(item["fold_no"]),
            str(item["metric_name"]),
            float(item["metric_value"]),
        )
        for item in export.fold_metrics
    }
    actual_folds = {
        (
            None if item["split_set_id"] is None else str(item["split_set_id"]),
            int(item["fold_no"]),
            str(item["metric_name"]),
            float(item["metric_value"]),
        )
        for item in fold_rows
    }
    if actual_folds != expected_folds:
        conflicts.append(
            f"fold metrics expected={sorted(expected_folds)!r} stored={sorted(actual_folds)!r}"
        )
    return conflicts


def _completed_package(
    connection: Connection,
    *,
    prepared: PreparedPublication,
    rate_package_id: int,
    was_existing: bool,
    deduplicated: bool,
) -> CompletedModelPublishResult:
    rows = (
        connection.execute(
            text(
                """
                SELECT
                    rp.model_id,
                    pm.model_name,
                    rp.model_version,
                    rp.source_export_id,
                    rp.rate_package_id,
                    rp.package_version,
                    rp.package_status,
                    rp.parent_rate_package_id,
                    rp.effective_from_date,
                    rp.effective_to_date,
                    rp.source_file,
                    rp.publication_receipt_sha256 AS package_publication_receipt_sha256,
                    mr.model_run_id,
                    mr.parent_model_run_id,
                    mr.run_status,
                    mr.export_id AS run_export_id,
                    mr.model_id AS run_model_id,
                    mr.model_name AS run_model_name,
                    mr.model_version AS run_model_version,
                    mr.manifest_id,
                    split_link.split_set_id,
                    mr.model_kind,
                    mr.model_equivalence_sha256,
                    mr.rating_workbook_path,
                    mr.rating_workbook_sha256,
                    mr.mlflow_run_id,
                    mr.publication_receipt_path,
                    mr.publication_receipt_sha256,
                    mr.dag_id,
                    mr.airflow_run_id,
                    mr.candidate_artifact_path,
                    mr.candidate_artifact_sha256,
                    mr.candidate_artifact_format,
                    mr.candidate_artifact_size_bytes,
                    mr.candidate_python_version,
                    mr.candidate_superglm_version,
                    mr.model_source_sha256
                FROM pricing.PRICING_RATE_PACKAGE AS rp WITH (UPDLOCK, HOLDLOCK)
                JOIN pricing.PRICING_MODEL AS pm
                  ON pm.model_id = rp.model_id
                JOIN pricing.MODEL_RUN AS mr WITH (UPDLOCK, HOLDLOCK)
                  ON mr.rate_package_id = rp.rate_package_id
                LEFT JOIN mlops.MODEL_RUN_SPLIT_SET AS split_link
                  ON split_link.model_run_id = mr.model_run_id
                 AND split_link.manifest_id = mr.manifest_id
                 AND split_link.dataset_role = 'training'
                 AND split_link.split_role = 'validation'
                WHERE rp.rate_package_id = :rate_package_id
                """
            ),
            {"rate_package_id": rate_package_id},
        )
        .mappings()
        .all()
    )
    if len(rows) != 1:
        raise RuntimeError("published package must resolve exactly one successful model run")
    row = rows[0]
    build = prepared.build
    package_status = str(row["package_status"]).upper()
    if package_status != "PUBLISHED":
        raise RuntimeError("existing model package is not PUBLISHED")
    mismatches = []
    for field, value in (
        ("model_id", build.model_id),
        ("model_name", build.model_name),
        ("manifest_id", build.manifest_id),
        ("model_kind", build.model_kind),
        ("model_equivalence_sha256", build.model_equivalence_sha256),
        ("run_status", "SUCCESS"),
    ):
        if _identity_text(row[field]) != _identity_text(value):
            mismatches.append(field)
    if mismatches:
        raise RuntimeError(
            "published package has incompatible durable lineage: " + ", ".join(mismatches)
        )
    if not deduplicated:
        evidence_params = {"model_run_id": int(row["model_run_id"])}
        dataset_rows = [
            dict(item)
            for item in connection.execute(
                text(
                    "SELECT manifest_id, dataset_role "
                    "FROM mlops.MODEL_RUN_DATASET "
                    "WHERE model_run_id = :model_run_id"
                ),
                evidence_params,
            )
            .mappings()
            .all()
        ]
        split_rows = [
            dict(item)
            for item in connection.execute(
                text(
                    "SELECT manifest_id, split_set_id, dataset_role, split_role "
                    "FROM mlops.MODEL_RUN_SPLIT_SET "
                    "WHERE model_run_id = :model_run_id"
                ),
                evidence_params,
            )
            .mappings()
            .all()
        ]
        metric_rows = [
            dict(item)
            for item in connection.execute(
                text(
                    "SELECT metric_name, metric_value, metric_scope "
                    "FROM mlops.MODEL_RUN_METRIC "
                    "WHERE model_run_id = :model_run_id"
                ),
                evidence_params,
            )
            .mappings()
            .all()
        ]
        fold_rows = [
            dict(item)
            for item in connection.execute(
                text(
                    "SELECT split_set_id, fold_no, metric_name, metric_value "
                    "FROM pricing.CV_FOLD_METRIC "
                    "WHERE model_run_id = :model_run_id"
                ),
                evidence_params,
            )
            .mappings()
            .all()
        ]
        evidence_conflicts = _retry_evidence_conflicts(
            row=dict(row),
            prepared=prepared,
            dataset_rows=dataset_rows,
            split_rows=split_rows,
            metric_rows=metric_rows,
            fold_rows=fold_rows,
        )
        if evidence_conflicts:
            raise RuntimeError(
                "existing export has incompatible evidence: " + "; ".join(evidence_conflicts)
            )
        committed_workbook = Path(str(row["rating_workbook_path"])).expanduser().resolve()
        allowed_root = prepared.allowed_artifact_root
        if allowed_root is not None and not committed_workbook.is_relative_to(
            Path(allowed_root).expanduser().resolve()
        ):
            raise RuntimeError("existing rating workbook is outside the configured artifact root")
        if not committed_workbook.is_file():
            raise RuntimeError("existing rating workbook is missing")
        if sha256_file(committed_workbook) != str(row["rating_workbook_sha256"]):
            raise RuntimeError("existing rating workbook SHA-256 verification failed")

        artifact_fields = (
            "candidate_artifact_path",
            "candidate_artifact_sha256",
            "candidate_artifact_format",
            "candidate_artifact_size_bytes",
            "candidate_python_version",
            "candidate_superglm_version",
            "model_source_sha256",
        )
        artifact_values = [row[field] for field in artifact_fields]
        if any(value is not None for value in artifact_values):
            if any(value is None for value in artifact_values):
                raise RuntimeError(
                    "existing successful run has incomplete candidate artifact metadata"
                )
            if allowed_root is None:
                raise RuntimeError(
                    "existing candidate artifact requires a configured verification root"
                )
            from pricing_pipeline.workbench.artifacts import (
                CandidateArtifactError,
                load_candidate_bundle,
            )

            try:
                bundle = load_candidate_bundle(
                    row["candidate_artifact_path"],
                    expected_sha256=row["candidate_artifact_sha256"],
                    expected_size_bytes=int(row["candidate_artifact_size_bytes"]),
                    expected_format=row["candidate_artifact_format"],
                    expected_python_version=row["candidate_python_version"],
                    expected_superglm_version=row["candidate_superglm_version"],
                    allowed_root=allowed_root,
                )
            except CandidateArtifactError as exc:
                raise RuntimeError(
                    f"existing candidate artifact failed verification: {exc}"
                ) from exc
            for field, value in (
                ("model_name", row["run_model_name"]),
                ("model_version", row["run_model_version"]),
                ("export_id", row["run_export_id"]),
            ):
                if getattr(bundle, field) != str(value):
                    raise RuntimeError(
                        f"existing candidate artifact {field} does not match model-run lineage"
                    )
            if bundle.model_source_sha256 != str(row["model_source_sha256"]):
                raise RuntimeError(
                    "existing candidate artifact source hash does not match model-run lineage"
                )
            if bundle.manifest_id != str(row["manifest_id"]):
                raise RuntimeError(
                    "existing candidate artifact manifest does not match model-run lineage"
                )
            resolved_split = None if row["split_set_id"] is None else str(row["split_set_id"])
            if bundle.split_set_id != resolved_split:
                raise RuntimeError(
                    "existing candidate artifact split set does not match model-run lineage"
                )
    return CompletedModelPublishResult(
        model_id=int(row["model_id"]),
        model_name=str(row["model_name"]),
        model_version=str(row["model_version"]),
        manifest_id=str(row["manifest_id"]),
        split_set_id=None if row["split_set_id"] is None else str(row["split_set_id"]),
        export_id=str(row["source_export_id"]),
        rate_package_id=int(row["rate_package_id"]),
        package_version=int(row["package_version"]),
        package_status=package_status,
        rating_workbook_path=str(row["rating_workbook_path"]),
        model_run_id=int(row["model_run_id"]),
        mlflow_run_id=str(row["mlflow_run_id"] or "") or None,
        publication_receipt_path=(
            None
            if row["publication_receipt_path"] is None
            else str(row["publication_receipt_path"])
        ),
        publication_receipt_sha256=(
            None
            if row["publication_receipt_sha256"] is None
            else str(row["publication_receipt_sha256"])
        ),
        was_existing=was_existing,
        deduplicated=deduplicated,
        model_kind=str(row["model_kind"]),
        model_equivalence_sha256=str(row["model_equivalence_sha256"]),
    )


def _resolve_existing_or_equivalent(
    connection: Connection,
    prepared: PreparedPublication,
    tables: RatingTables,
) -> CompletedModelPublishResult | None:
    build = prepared.build
    revision_metadata_json = canonical_revision_metadata(prepared.revision_metadata)
    existing = (
        connection.execute(
            text(
                """
                SELECT
                    rate_package_id,
                    package_version,
                    model_id,
                    model_name,
                    model_version,
                    effective_from_date,
                    effective_to_date,
                    package_status,
                    source_export_id,
                    source_file,
                    publication_receipt_sha256,
                    staging_content_sha256,
                    parent_rate_package_id,
                    revision_metadata_json
                FROM pricing.PRICING_RATE_PACKAGE WITH (UPDLOCK, HOLDLOCK)
                WHERE model_id = :model_id
                  AND source_export_id = :export_id
                """
            ),
            {"model_id": build.model_id, "export_id": build.export_id},
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        conflicts = _existing_export_conflicts(
            existing,
            _prepared_staged_metadata(prepared, tables),
            parent_rate_package_id=prepared.parent_rate_package_id,
            revision_metadata_json=revision_metadata_json,
        )
        if conflicts:
            raise ValueError(
                f"export_id {build.export_id!r} is already published with "
                "incompatible metadata: " + "; ".join(conflicts)
            )
        if str(existing["package_status"]).upper() != "PUBLISHED":
            raise RuntimeError("existing model package is not PUBLISHED")
        return _completed_package(
            connection,
            prepared=prepared,
            rate_package_id=int(existing["rate_package_id"]),
            was_existing=True,
            deduplicated=False,
        )

    equivalent = (
        connection.execute(
            text(
                """
                SELECT
                    rp.rate_package_id,
                    rp.package_status,
                    rp.effective_from_date,
                    pm.model_name,
                    mr.model_run_id,
                    split_link.manifest_id AS split_manifest_id
                FROM pricing.MODEL_RUN AS mr WITH (UPDLOCK, HOLDLOCK)
                JOIN pricing.PRICING_RATE_PACKAGE AS rp
                  ON rp.rate_package_id = mr.rate_package_id
                JOIN pricing.PRICING_MODEL AS pm
                  ON pm.model_id = mr.model_id
                LEFT JOIN mlops.MODEL_RUN_SPLIT_SET AS split_link
                  ON split_link.model_run_id = mr.model_run_id
                 AND split_link.dataset_role = 'training'
                 AND split_link.split_role = 'validation'
                WHERE mr.model_id = :model_id
                  AND mr.manifest_id = :manifest_id
                  AND mr.model_kind = :model_kind
                  AND mr.model_equivalence_sha256 = :model_equivalence_sha256
                  AND mr.run_status = 'SUCCESS'
                ORDER BY rp.package_version
                """
            ),
            {
                "model_id": build.model_id,
                "manifest_id": build.manifest_id,
                "model_kind": build.model_kind,
                "model_equivalence_sha256": tables.model_equivalence_sha256,
            },
        )
        .mappings()
        .all()
    )
    if not equivalent:
        return None
    if len(equivalent) > 1:
        model_run_ids = {str(row["model_run_id"]) for row in equivalent}
        if len(model_run_ids) == 1:
            raise RuntimeError(
                "equivalent model run resolves multiple training/validation split links"
            )
        raise RuntimeError("equivalent rating fingerprint resolves multiple successful model runs")
    equivalent = equivalent[0]
    if str(equivalent["package_status"]).upper() != "PUBLISHED":
        raise RuntimeError("equivalent model package is not PUBLISHED")
    if str(equivalent["model_name"]) != build.model_name:
        raise RuntimeError("equivalent model run has a different model name")
    if equivalent["split_manifest_id"] is not None and str(equivalent["split_manifest_id"]) != str(
        build.manifest_id
    ):
        raise RuntimeError("equivalent model run split lineage points at a different manifest")
    if _identity_text(equivalent["effective_from_date"]) != _identity_text(build.effective_from):
        raise RuntimeError(
            "an equivalent model build already exists under a different effective_from date"
        )
    training_links = connection.execute(
        text(
            "SELECT COUNT(*) FROM mlops.MODEL_RUN_DATASET "
            "WHERE model_run_id = :model_run_id "
            "AND manifest_id = :manifest_id AND dataset_role = 'training'"
        ),
        {
            "model_run_id": equivalent["model_run_id"],
            "manifest_id": build.manifest_id,
        },
    ).scalar_one()
    if int(training_links) != 1:
        raise RuntimeError(
            "equivalent model run does not have exactly one matching training-manifest link"
        )
    connection.execute(
        text(
            """
            DELETE FROM pricing.PRICING_MODEL_VERSION_RESERVATION
            WHERE model_id = :model_id
              AND export_id = :export_id
            """
        ),
        {"model_id": build.model_id, "export_id": build.export_id},
    )
    return _completed_package(
        connection,
        prepared=prepared,
        rate_package_id=int(equivalent["rate_package_id"]),
        was_existing=True,
        deduplicated=True,
    )


def _replace_staging_frames(
    connection: Connection,
    prepared: PreparedPublication,
    tables: RatingTables,
) -> None:
    for field_name, digest in (
        ("staging_content_sha256", tables.staging_content_sha256),
        ("model_equivalence_sha256", tables.model_equivalence_sha256),
    ):
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    export_id = prepared.build.export_id
    params = {"export_id": export_id}
    for table in (
        "STG_TERM_METADATA",
        "STG_CELL_LEVEL",
        "STG_RATE_CELL",
        "STG_RATING_EXPORT",
    ):
        connection.execute(
            text(f"DELETE FROM pricing_stg.{table} WHERE export_id = :export_id"),
            params,
        )
    schemas = schema_names_from_connectable(connection)
    tables.export_frame.to_sql(
        "STG_RATING_EXPORT",
        connection,
        schema=schemas.pricing_staging,
        if_exists="append",
        index=False,
    )
    connection.execute(
        text(
            "UPDATE pricing_stg.STG_RATING_EXPORT "
            "SET model_id = :model_id, "
            "staging_content_sha256 = :staging_content_sha256, "
            "model_equivalence_sha256 = :model_equivalence_sha256 "
            "WHERE export_id = :export_id"
        ),
        {
            "export_id": export_id,
            "model_id": prepared.build.model_id,
            "staging_content_sha256": tables.staging_content_sha256,
            "model_equivalence_sha256": tables.model_equivalence_sha256,
        },
    )
    for frame, table in (
        (tables.rate_cells, "STG_RATE_CELL"),
        (tables.cell_levels, "STG_CELL_LEVEL"),
    ):
        frame.to_sql(
            table,
            connection,
            schema=schemas.pricing_staging,
            if_exists="append",
            index=False,
            chunksize=5000,
        )
    if not tables.term_metadata.empty:
        tables.term_metadata.to_sql(
            "STG_TERM_METADATA",
            connection,
            schema=schemas.pricing_staging,
            if_exists="append",
            index=False,
            chunksize=5000,
        )


def _insert_draft_package(
    connection: Connection,
    prepared: PreparedPublication,
    tables: RatingTables,
) -> _DraftPackage:
    """Validate release intent and insert the one prepared DRAFT package."""
    build = prepared.build
    export_id = build.export_id
    export = {
        name: None if pd.isna(value) else value
        for name, value in tables.export_frame.iloc[0].items()
    }
    model_id = build.model_id
    if model_id is None:
        raise ModelRegistryError(f"prepared export {export_id!r} is missing a registered model_id")
    release = {
        "export_id": export_id,
        "model_name": build.model_name,
        "model_version": build.model_version,
        "effective_from_date": build.effective_from,
        "effective_to_date": prepared.effective_to,
        "source_file": str(Path(build.rating_workbook_path).resolve()),
        "publication_receipt_sha256": build.publication_receipt_sha256,
        "created_by": build.created_by,
    }
    changed = [
        field
        for field, expected in release.items()
        if _identity_text(export.get(field)) != _identity_text(expected)
    ]
    if changed:
        raise ValueError(
            "prepared rating-table release identity changed before publication: "
            + ", ".join(changed)
        )

    parent_id = prepared.parent_rate_package_id
    if parent_id is not None:
        parent = (
            connection.execute(
                text(
                    """
                    SELECT model_id, model_version, effective_from_date,
                           effective_to_date, package_status
                    FROM pricing.PRICING_RATE_PACKAGE WITH (UPDLOCK, HOLDLOCK)
                    WHERE rate_package_id = :parent_rate_package_id
                    """
                ),
                {"parent_rate_package_id": parent_id},
            )
            .mappings()
            .one_or_none()
        )
        if parent is None:
            raise ValueError(f"parent rate package {parent_id} does not exist")
        if int(parent["model_id"]) != int(model_id):
            raise ValueError("parent rate package belongs to a different model")
        if str(parent["package_status"]) != "PUBLISHED":
            raise ValueError("parent rate package must have PUBLISHED status")
        for field in ("model_version", "effective_from_date", "effective_to_date"):
            if _identity_text(parent[field]) != _identity_text(release[field]):
                raise ValueError(
                    f"parent {field}={parent[field]!r} does not match "
                    f"prepared {field}={release[field]!r}"
                )
    else:
        model_version = _identity_text(release["model_version"])
        if model_version is None:
            raise ValueError("root package publication requires model_version")
        reservation = (
            connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM pricing.PRICING_MODEL_VERSION_RESERVATION WITH (UPDLOCK, HOLDLOCK)
                    WHERE model_id = :model_id AND export_id = :export_id
                    """
                ),
                {"model_id": model_id, "export_id": export_id},
            )
            .mappings()
            .one_or_none()
        )
        if reservation is None:
            connection.execute(
                text(
                    """
                    INSERT INTO pricing.PRICING_MODEL_VERSION_RESERVATION (
                        model_id, export_id, model_version
                    ) VALUES (:model_id, :export_id, :model_version)
                    """
                ),
                {
                    "model_id": model_id,
                    "export_id": export_id,
                    "model_version": model_version,
                },
            )
        elif _identity_text(reservation["model_version"]) != model_version:
            raise ValueError(
                f"reserved model_version {reservation['model_version']!r} does not match "
                f"prepared model_version {model_version!r} for export_id={export_id!r}"
            )

    offset_handling = export["offset_handling"] or "UNKNOWN"
    offset_factor_name = export["offset_factor_name"]
    offset_terms = tables.rate_cells.loc[
        tables.rate_cells["term_type"] == "OFFSET_FACTOR", "term_name"
    ]
    if offset_handling == "EXPORTED_FACTOR" and (
        not offset_factor_name or str(offset_factor_name) not in set(offset_terms)
    ):
        raise ValueError("prepared EXPORTED_FACTOR publication has no matching OFFSET_FACTOR term")
    if offset_handling == "ALREADY_APPLIED_SQL_EXPOSURE" and not offset_terms.empty:
        raise ValueError(
            "prepared ALREADY_APPLIED_SQL_EXPOSURE publication contains an OFFSET_FACTOR term"
        )

    package_version = connection.execute(
        text(
            """
            SELECT ISNULL(MAX(package_version), 0) + 1
            FROM pricing.PRICING_RATE_PACKAGE WITH (UPDLOCK, HOLDLOCK)
            WHERE model_id = :model_id
            """
        ),
        {"model_id": model_id},
    ).scalar_one()
    params = {
        "parent_rate_package_id": parent_id,
        "model_id": int(model_id),
        "model_name": release["model_name"],
        "model_version": release["model_version"],
        "package_version": package_version,
        "base_rate": export["base_rate"],
        "effective_from_date": release["effective_from_date"],
        "effective_to_date": release["effective_to_date"],
        "package_status": "DRAFT",
        "source_export_id": export_id,
        "source_file": release["source_file"],
        "publication_receipt_json": export["publication_receipt_json"],
        "publication_receipt_sha256": release["publication_receipt_sha256"],
        "staging_content_sha256": tables.staging_content_sha256,
        "package_metadata_json": export["package_metadata_json"],
        "revision_metadata_json": canonical_revision_metadata(prepared.revision_metadata),
        "offset_handling": offset_handling,
        "offset_factor_name": offset_factor_name,
        "offset_source_name": export["offset_source_name"],
        "offset_label": export["offset_label"],
        "metadata_origin": export["metadata_origin"],
        "created_by": release["created_by"],
    }
    rate_package_id = connection.execute(
        text(
            """
            INSERT INTO pricing.PRICING_RATE_PACKAGE (
                parent_rate_package_id, model_id, model_name, model_version,
                package_version, base_rate, effective_from_date, effective_to_date,
                package_status, source_export_id, source_file,
                publication_receipt_json, publication_receipt_sha256,
                staging_content_sha256, package_metadata_json, revision_metadata_json,
                offset_handling, offset_factor_name, offset_source_name, offset_label,
                metadata_origin, created_by
            )
            OUTPUT INSERTED.rate_package_id
            VALUES (
                :parent_rate_package_id, :model_id, :model_name, :model_version,
                :package_version, :base_rate, :effective_from_date, :effective_to_date,
                :package_status, :source_export_id, :source_file,
                :publication_receipt_json, :publication_receipt_sha256,
                :staging_content_sha256, :package_metadata_json, :revision_metadata_json,
                :offset_handling, :offset_factor_name, :offset_source_name, :offset_label,
                :metadata_origin, :created_by
            )
            """
        ),
        params,
    ).scalar_one()
    return _DraftPackage(
        rate_package_id=int(rate_package_id),
        package_version=int(package_version),
        model_id=int(model_id),
        export_id=export_id,
    )


def _insert_rating_tables(
    connection: Connection,
    package: _DraftPackage,
    tables: RatingTables | None,
) -> None:
    del tables
    connection.execute(
        text("""
        -- Features
        INSERT INTO pricing.PRICING_FEATURE (
            feature_name,
            feature_value_type,
            is_ordered
        )
        SELECT DISTINCT
            s.feature_name,
            s.feature_value_type,
            CASE WHEN s.level_set_type IN ('NUMERIC_BAND', 'SPLINE_GRID_1D') THEN 1 ELSE 0 END
        FROM pricing_stg.STG_CELL_LEVEL s
        WHERE s.export_id = :export_id
          AND NOT EXISTS (
              SELECT 1
              FROM pricing.PRICING_FEATURE f
              WHERE f.feature_name = s.feature_name
          );
        -- Level sets
        INSERT INTO pricing.PRICING_FEATURE_LEVEL_SET (
            feature_id,
            model_id,
            level_set_name,
            level_set_type,
            binning_strategy,
            grid_width
        )
        SELECT DISTINCT
            f.feature_id,
            :model_id,
            s.level_set_name,
            s.level_set_type,
            CASE
                WHEN s.level_set_type = 'SPLINE_GRID_1D' THEN 'SPLINE_EVAL_GRID'
                WHEN s.level_set_type = 'NUMERIC_BAND' THEN 'EXPLICIT_BANDS'
                ELSE 'EXPLICIT_LEVELS'
            END,
            NULL
        FROM pricing_stg.STG_CELL_LEVEL s
        JOIN pricing.PRICING_FEATURE f
          ON f.feature_name = s.feature_name
        WHERE s.export_id = :export_id
          AND NOT EXISTS (
              SELECT 1
              FROM pricing.PRICING_FEATURE_LEVEL_SET ls
              WHERE ls.model_id = :model_id
                AND ls.feature_id = f.feature_id
                AND ls.level_set_name = s.level_set_name
          );
        -- Levels
        INSERT INTO pricing.PRICING_FEATURE_LEVEL (
            level_set_id,
            level_code,
            level_label,
            order_index,
            lower_bound,
            upper_bound,
            representative_value,
            is_missing,
            is_other
        )
        SELECT DISTINCT
            ls.level_set_id,
            s.level_code,
            s.level_label,
            s.order_index,
            s.lower_bound,
            s.upper_bound,
            s.representative_value,
            s.is_missing,
            s.is_other
        FROM pricing_stg.STG_CELL_LEVEL s
        JOIN pricing.PRICING_FEATURE f
          ON f.feature_name = s.feature_name
        JOIN pricing.PRICING_FEATURE_LEVEL_SET ls
          ON ls.model_id = :model_id
         AND ls.feature_id = f.feature_id
         AND ls.level_set_name = s.level_set_name
        WHERE s.export_id = :export_id
          AND NOT EXISTS (
              SELECT 1
              FROM pricing.PRICING_FEATURE_LEVEL fl
              WHERE fl.level_set_id = ls.level_set_id
                AND fl.level_code = s.level_code
          )
        ORDER BY
            ls.level_set_id,
            s.order_index,
            s.lower_bound,
            s.upper_bound,
            s.level_code;
        -- Terms
        INSERT INTO pricing.PRICING_TERM (
            rate_package_id,
            term_name,
            term_type,
            sequence_no,
            term_metadata_json
        )
        SELECT DISTINCT
            :rate_package_id,
            c.term_name,
            c.term_type,
            c.sequence_no,
            tm.term_metadata_json
        FROM pricing_stg.STG_RATE_CELL c
        LEFT JOIN pricing_stg.STG_TERM_METADATA tm
          ON tm.export_id = c.export_id
         AND tm.term_name = c.term_name
        WHERE c.export_id = :export_id;
        -- Term features
        INSERT INTO pricing.PRICING_TERM_FEATURE (
            term_id,
            position_no,
            feature_id,
            level_set_id,
            input_column_name
        )
        SELECT DISTINCT
            t.term_id,
            s.position_no,
            f.feature_id,
            ls.level_set_id,
            s.feature_name
        FROM pricing_stg.STG_CELL_LEVEL s
        JOIN pricing_stg.STG_RATE_CELL c
          ON c.export_id = s.export_id
         AND c.row_id = s.row_id
        JOIN pricing.PRICING_TERM t
          ON t.rate_package_id = :rate_package_id
         AND t.term_name = c.term_name
        JOIN pricing.PRICING_FEATURE f
          ON f.feature_name = s.feature_name
        JOIN pricing.PRICING_FEATURE_LEVEL_SET ls
          ON ls.model_id = :model_id
         AND ls.feature_id = f.feature_id
         AND ls.level_set_name = s.level_set_name
        WHERE s.export_id = :export_id;
        -- Cells
        INSERT INTO pricing.PRICING_RATE_CELL (
            term_id,
            cell_key_text,
            cell_key_digest,
            multiplier,
            log_coefficient,
            exposure_weight,
            record_count,
            is_reference,
            is_default
        )
        SELECT
            t.term_id,
            c.cell_key_text,
            HASHBYTES('SHA2_256', c.cell_key_text),
            c.multiplier,
            c.log_coefficient,
            c.exposure_weight,
            c.record_count,
            c.is_reference,
            c.is_default
        FROM pricing_stg.STG_RATE_CELL c
        JOIN pricing.PRICING_TERM t
          ON t.rate_package_id = :rate_package_id
         AND t.term_name = c.term_name
        WHERE c.export_id = :export_id;
        -- Cell-level mapping
        INSERT INTO pricing.PRICING_RATE_CELL_LEVEL (
            cell_id,
            position_no,
            feature_level_id
        )
        SELECT
            rc.cell_id,
            s.position_no,
            fl.feature_level_id
        FROM pricing_stg.STG_CELL_LEVEL s
        JOIN pricing_stg.STG_RATE_CELL c
          ON c.export_id = s.export_id
         AND c.row_id = s.row_id
        JOIN pricing.PRICING_TERM t
          ON t.rate_package_id = :rate_package_id
         AND t.term_name = c.term_name
        JOIN pricing.PRICING_RATE_CELL rc
          ON rc.term_id = t.term_id
         AND rc.cell_key_text = c.cell_key_text
        JOIN pricing.PRICING_FEATURE f
          ON f.feature_name = s.feature_name
        JOIN pricing.PRICING_FEATURE_LEVEL_SET ls
          ON ls.model_id = :model_id
         AND ls.feature_id = f.feature_id
         AND ls.level_set_name = s.level_set_name
        JOIN pricing.PRICING_FEATURE_LEVEL fl
          ON fl.level_set_id = ls.level_set_id
         AND fl.level_code = s.level_code
        WHERE s.export_id = :export_id;
        -- Minimal compile step: flat rate cells
        INSERT INTO pricing.PRICING_COMPILED_RATE_CELL (
            rate_package_id,
            term_id,
            cell_key_digest,
            term_name,
            term_type,
            sequence_no,
            cell_key_text,
            multiplier,
            log_coefficient,
            exposure_weight,
            record_count,
            is_default,
            is_reference
        )
        SELECT
            :rate_package_id,
            t.term_id,
            c.cell_key_digest,
            t.term_name,
            t.term_type,
            t.sequence_no,
            c.cell_key_text,
            c.multiplier,
            c.log_coefficient,
            c.exposure_weight,
            c.record_count,
            c.is_default,
            c.is_reference
        FROM pricing.PRICING_TERM t
        JOIN pricing.PRICING_RATE_CELL c
          ON c.term_id = t.term_id
        WHERE t.rate_package_id = :rate_package_id
          AND c.is_deleted = 0;
        -- Compile 1D bands for spline/numeric-band terms
        INSERT INTO pricing.PRICING_COMPILED_1D_RATE_BAND (
            rate_package_id,
            term_id,
            feature_level_id,
            term_name,
            feature_name,
            level_code,
            sort_order,
            lower_bound,
            upper_bound,
            representative_value,
            multiplier,
            log_coefficient
        )
        SELECT
            :rate_package_id,
            t.term_id,
            fl.feature_level_id,
            t.term_name,
            f.feature_name,
            fl.level_code,
            COALESCE(fl.order_index, 0),
            fl.lower_bound,
            CASE
                WHEN ROW_NUMBER() OVER (
                    PARTITION BY t.term_id
                    ORDER BY
                        CASE WHEN fl.lower_bound IS NULL THEN 1 ELSE 0 END,
                        fl.lower_bound DESC,
                        COALESCE(fl.order_index, 0) DESC,
                        fl.feature_level_id DESC
                ) = 1 THEN NULL
                ELSE fl.upper_bound
            END,
            fl.representative_value,
            rc.multiplier,
            rc.log_coefficient
        FROM pricing.PRICING_TERM t
        JOIN pricing.PRICING_RATE_CELL rc
          ON rc.term_id = t.term_id
        JOIN pricing.PRICING_RATE_CELL_LEVEL rcl
          ON rcl.cell_id = rc.cell_id
         AND rcl.position_no = 1
        JOIN pricing.PRICING_FEATURE_LEVEL fl
          ON fl.feature_level_id = rcl.feature_level_id
        JOIN pricing.PRICING_FEATURE_LEVEL_SET ls
          ON ls.level_set_id = fl.level_set_id
        JOIN pricing.PRICING_FEATURE f
          ON f.feature_id = ls.feature_id
        WHERE t.rate_package_id = :rate_package_id
          AND (
              t.term_type IN ('DISCRETIZED_SPLINE_1D', 'NUMERIC_BANDED_1D')
              OR (
                  t.term_type = 'OFFSET_FACTOR'
                  AND ls.level_set_type IN ('NUMERIC_BAND', 'SPLINE_GRID_1D')
              )
          )
          AND rc.is_deleted = 0
        ORDER BY
            t.sequence_no,
            COALESCE(fl.order_index, 0),
            fl.lower_bound,
            fl.upper_bound,
            fl.level_code;
        """),
        {
            "export_id": package.export_id,
            "rate_package_id": package.rate_package_id,
            "model_id": package.model_id,
        },
    )


def _insert_lineage(
    connection: Connection,
    package: _DraftPackage,
    prepared: PreparedPublication,
) -> int:
    return record_model_run(
        None,
        build=prepared.build,
        dag_id=prepared.execution_name,
        airflow_run_id=prepared.execution_id,
        rate_package_id=package.rate_package_id,
        parent_model_run_id=prepared.parent_model_run_id,
        connection=connection,
    )


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if pd.isna(value):
        return None
    return str(value)


def verify_package_sql_parity(
    connection: Connection,
    *,
    rate_package_id: int,
    edited_model: Any,
    bundle: CandidateBundle,
    publication_receipt: SuperGLMPublicationReceipt | None = None,
    sample_size: int = 50,
    rtol: float = 1e-4,
    atol: float = 1e-8,
) -> None:
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    count = min(int(sample_size), len(bundle.X))
    if count == 0:
        raise EditorSubmissionError("cannot verify SQL parity on an empty candidate")
    sample = bundle.X.iloc[:count]
    sample_offset = None if bundle.offset is None else np.asarray(bundle.offset)[:count]
    if sample_offset is None:
        expected = np.asarray(edited_model.predict(sample), dtype=float)
    else:
        expected = np.asarray(edited_model.predict(sample, offset=sample_offset), dtype=float)
    contract = bundle.offset_contract
    sample_published_offset_source = (
        pd.Series(bundle.offset_source).reset_index(drop=True).iloc[:count]
        if contract.handling == "EXPORTED_FACTOR"
        else None
    )
    published_by_source: dict[str, str] = {}
    if publication_receipt is not None:
        for metadata in publication_receipt.term_metadata.values():
            feature_kind = metadata.get("feature_kind")
            if feature_kind == "categorical_interaction":
                source_names = metadata.get("parent_names")
                published_names = metadata.get("input_column_names")
                if isinstance(source_names, list | tuple) and isinstance(
                    published_names, list | tuple
                ):
                    published_by_source.update(
                        (str(source), str(published))
                        for source, published in zip(
                            source_names,
                            published_names,
                            strict=True,
                        )
                    )
                continue
            if feature_kind == "offset":
                continue
            source_name = metadata.get("source_term_name")
            published_name = metadata.get("published_term_name")
            if source_name is not None and published_name is not None:
                published_by_source[str(source_name)] = str(published_name)

    schemas = schema_names_from_connectable(connection)
    statement = text(
        f"""
        EXEC {schemas.pricing}.PREDICT_RATE_PACKAGE
            @rate_package_id = :rate_package_id,
            @features_json = :features_json,
            @exposure = :exposure,
            @include_breakdown = 0
        """
    )
    for position, (_, row) in enumerate(sample.iterrows()):
        features = {
            published_by_source.get(str(name), str(name)): _json_value(value)
            for name, value in row.items()
        }
        exposure = 1.0
        if sample_published_offset_source is not None:
            features[str(contract.published_factor_name)] = _json_value(
                sample_published_offset_source.iloc[position]
            )
        elif sample_offset is not None and contract.handling == "ALREADY_APPLIED_SQL_EXPOSURE":
            exposure = float(np.exp(sample_offset[position]))
        params = {
            "rate_package_id": int(rate_package_id),
            "features_json": canonical_json(features),
            "exposure": exposure,
        }
        actual = float(connection.execute(statement, params).mappings().one()["prediction"])
        if not np.isclose(actual, expected[position], rtol=rtol, atol=atol):
            raise EditorSubmissionError(
                f"edited package {int(rate_package_id)} failed Python/SQL parity verification"
            )


def _verify_draft(
    connection: Connection,
    package: _DraftPackage,
    verification: DraftVerification | None,
) -> None:
    if verification is None:
        return
    verify_package_sql_parity(
        connection,
        rate_package_id=package.rate_package_id,
        edited_model=verification.model,
        bundle=verification.bundle,
        publication_receipt=verification.receipt,
    )


def _mark_published(connection: Connection, rate_package_id: int) -> None:
    connection.execute(
        text(
            """
            UPDATE pricing.PRICING_RATE_PACKAGE
            SET package_status = :package_status
            WHERE rate_package_id = :rate_package_id;
            """
        ),
        {"package_status": "PUBLISHED", "rate_package_id": rate_package_id},
    )


def _publication_result(
    package: _DraftPackage,
    model_run_id: int,
    prepared: PreparedPublication,
) -> CompletedModelPublishResult:
    build = prepared.build
    return CompletedModelPublishResult(
        model_id=package.model_id,
        model_name=build.model_name,
        model_version=build.model_version,
        manifest_id=build.manifest_id,
        split_set_id=build.split_set_id,
        export_id=package.export_id,
        rate_package_id=package.rate_package_id,
        package_version=package.package_version,
        package_status="PUBLISHED",
        rating_workbook_path=build.rating_workbook_path,
        model_run_id=model_run_id,
        mlflow_run_id=build.mlflow_run_id or None,
        publication_receipt_path=build.publication_receipt_path,
        publication_receipt_sha256=build.publication_receipt_sha256,
        was_existing=False,
        deduplicated=False,
        model_kind=build.model_kind,
        model_equivalence_sha256=build.model_equivalence_sha256,
    )


def publish_sqlserver(
    engine: Engine,
    prepared: PreparedPublication,
    tables: RatingTables,
) -> CompletedModelPublishResult:
    with engine.begin() as connection:
        _lock_export(connection, prepared.build.export_id)
        existing = _resolve_existing_or_equivalent(connection, prepared, tables)
        if existing is not None:
            _delete_staging_children(connection, export_id=prepared.build.export_id)
            return existing
        _replace_staging_frames(connection, prepared, tables)
        package = _insert_draft_package(connection, prepared, tables)
        _insert_rating_tables(connection, package, tables)
        model_run_id = _insert_lineage(connection, package, prepared)
        _verify_draft(connection, package, prepared.verification)
        _mark_published(connection, package.rate_package_id)
        _delete_staging_children(connection, export_id=prepared.build.export_id)
        return _publication_result(package, model_run_id, prepared)


__all__ = [
    "publish_sqlserver",
    "verify_package_sql_parity",
]
