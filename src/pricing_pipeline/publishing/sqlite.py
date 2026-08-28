"""Publish prepared rating tables in one explicit SQLite transaction.

The concrete audit, package, rating-table, and lineage SQL intentionally stays
together so maintainers can verify the complete local transaction top-to-bottom.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from pricing_pipeline.infra.config import Settings
from pricing_pipeline.infra.offline_sqlite import local_publish_lock
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild, ApprovedModelBuildError
from pricing_pipeline.orchestration.publish_completed_build import (
    _verify_candidate_artifact,
    load_candidate_sql_lineage,
)
from pricing_pipeline.publishing.identity import (
    ModelEquivalenceError,
    canonical_revision_metadata,
    immutable_conflicts,
)
from pricing_pipeline.publishing.publish import (
    CompletedModelPublishResult,
    ModelRegistryError,
    PreparedPublication,
    PricingModelRecord,
    PublicationRequest,
    publish_candidate,
)
from pricing_pipeline.publishing.rating_tables import RatingTables
from pricing_pipeline.workbench.submission import sha256_file

_VERSION_PATTERN = re.compile(r"^v([0-9]+)$")


def _sqlite_model_record(connection, model_name: str) -> PricingModelRecord | None:
    row = (
        connection.execute(
            text(
                "SELECT model_id, model_name, model_label, target_name, model_type, model_status "
                "FROM pricing.PRICING_MODEL WHERE model_name = :model_name"
            ),
            {"model_name": model_name},
        )
        .mappings()
        .one_or_none()
    )
    return None if row is None else PricingModelRecord(**dict(row))


def _validate_sqlite_model(
    connection,
    config: ModelBuildConfig,
) -> PricingModelRecord:
    record = _sqlite_model_record(connection, config.model_name)
    if record is None:
        raise ModelRegistryError(f"model_name {config.model_name!r} is not registered")
    mismatches = [
        field
        for field, expected in (
            ("model_label", config.model_label),
            ("target_name", config.target_name),
            ("model_type", config.model_type),
        )
        if getattr(record, field) != expected
    ]
    if record.model_status != "ACTIVE":
        mismatches.append("model_status")
    if mismatches:
        raise ModelRegistryError(
            f"registered model {config.model_name!r} does not match config: "
            + ", ".join(mismatches)
        )
    return record


def register_sqlite_model(
    engine,
    config: ModelBuildConfig,
    *,
    created_by: str,
) -> PricingModelRecord:
    """Insert once and validate the complete stable model identity."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO pricing.PRICING_MODEL (
                    model_name, model_label, target_name, model_type, model_status, created_by
                ) VALUES (
                    :model_name, :model_label, :target_name, :model_type, 'ACTIVE', :created_by
                )
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
        return _validate_sqlite_model(connection, config)


def resolve_sqlite_model_version(
    engine,
    *,
    model_name: str,
    export_id: str,
) -> str:
    """Transactionally reserve one trained version for an export."""
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            model_id = int(
                connection.execute(
                    text(
                        "SELECT model_id FROM pricing.PRICING_MODEL WHERE model_name = :model_name"
                    ),
                    {"model_name": model_name},
                ).scalar_one()
            )
            params = {"model_id": model_id, "export_id": export_id}
            existing_versions = list(
                connection.execute(
                    text(
                        """
                        SELECT model_version FROM pricing.PRICING_RATE_PACKAGE
                        WHERE model_id = :model_id AND source_export_id = :export_id
                        UNION
                        SELECT model_version FROM pricing.PRICING_MODEL_VERSION_RESERVATION
                        WHERE model_id = :model_id AND export_id = :export_id
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
                connection.commit()
                return str(existing_versions[0])
            versions = connection.execute(
                text(
                    """
                    SELECT model_version FROM pricing.PRICING_RATE_PACKAGE
                    WHERE model_id = :model_id AND parent_rate_package_id IS NULL
                    UNION ALL
                    SELECT model_version FROM pricing.PRICING_MODEL_VERSION_RESERVATION
                    WHERE model_id = :model_id
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
                    """
                    INSERT INTO pricing.PRICING_MODEL_VERSION_RESERVATION (
                        model_id, export_id, model_version
                    ) VALUES (:model_id, :export_id, :model_version)
                    """
                ),
                {**params, "model_version": reserved},
            )
            connection.commit()
            return reserved
        except BaseException:
            connection.rollback()
            raise


def publish_sqlite_candidate(
    engine,
    *,
    settings: Settings,
    model_id: int,
    model_config: ModelBuildConfig,
    completed_build: ApprovedModelBuild,
    created_by: str,
) -> CompletedModelPublishResult:
    return _publish_sqlite_candidate_locked(
        engine,
        model_id=model_id,
        model_config=model_config,
        completed_build=completed_build,
        created_by=created_by,
        artifact_root=settings.workbench_artifact_root,
    )


def _publish_sqlite_candidate_locked(
    engine,
    *,
    model_id: int,
    model_config: ModelBuildConfig,
    completed_build: ApprovedModelBuild,
    created_by: str,
    artifact_root: str | Path,
) -> CompletedModelPublishResult:
    del created_by
    if not isinstance(completed_build, ApprovedModelBuild):
        raise TypeError("completed_build must be an ApprovedModelBuild")
    build = completed_build
    mismatches = [
        f"{field} build={actual!r} registered={expected!r}"
        for field, actual, expected in (
            ("model_id", build.model_id, model_id),
            ("model_name", build.model_name, model_config.model_name),
            ("model_type", build.model_type, model_config.model_type),
            ("target_name", build.target_name, model_config.target_name),
            ("deployment_slot", build.deployment_slot, model_config.deployment_slot),
        )
        if actual != expected
    ]
    if mismatches:
        raise ApprovedModelBuildError(
            "approved build does not match the registered model: " + "; ".join(mismatches)
        )
    workbook_path = Path(build.rating_workbook_path)
    if not workbook_path.is_file():
        raise ApprovedModelBuildError(
            f"rating_workbook_path does not exist: {workbook_path.as_posix()}"
        )
    actual_sha256 = sha256_file(workbook_path)
    if actual_sha256 != build.rating_workbook_sha256:
        raise ApprovedModelBuildError(
            "rating workbook SHA-256 does not match the completed build: "
            f"expected={build.rating_workbook_sha256!r}, actual={actual_sha256!r}"
        )
    manifest_id = str(build.manifest_id or "").strip()
    export_id = str(build.export_id or "").strip()
    if not manifest_id:
        raise ApprovedModelBuildError("local notebook publication requires an existing manifest_id")
    if not export_id:
        raise ApprovedModelBuildError("local notebook publication requires an export_id")
    if build.candidate_artifact_path is not None:
        _verify_candidate_artifact(
            build,
            sql_lineage=load_candidate_sql_lineage(
                engine,
                manifest_id=manifest_id,
                split_set_id=build.split_set_id,
            ),
            allowed_root=artifact_root,
        )
    return publish_candidate(
        engine,
        PublicationRequest(
            build=build,
            model_config=model_config,
            execution_name="notebook_local",
            execution_id=export_id,
            allowed_artifact_root=Path(artifact_root),
        ),
    )


_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _identity(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value)
    return cleaned or None


def _sql_value(value: object) -> object:
    if value is None:
        return None
    item = getattr(value, "item", None)
    if callable(item):
        value = item()
    missing = pd.isna(value)
    if isinstance(missing, bool) and missing:
        return None
    return value


def _date_identity(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    cleaned = str(value).strip()
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned).date().isoformat()
    except ValueError:
        return date.fromisoformat(cleaned).isoformat()


def _local_lock_root(engine: Engine, prepared: PreparedPublication) -> Path:
    if prepared.allowed_artifact_root is not None:
        return Path(prepared.allowed_artifact_root).expanduser().resolve().parent
    database = getattr(getattr(engine, "url", None), "database", None)
    if database:
        return Path(str(database)).expanduser().resolve().parent
    raise ValueError("SQLite publication requires an artifact root or file-backed engine")


@contextmanager
def _sqlite_publication_transaction(
    engine: Engine,
    prepared: PreparedPublication,
) -> Iterator[Connection]:
    with local_publish_lock(_local_lock_root(engine, prepared)), engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


def _export_metadata(
    prepared: PreparedPublication,
    tables: RatingTables,
) -> dict[str, object]:
    if len(tables.export_frame.index) != 1:
        raise ApprovedModelBuildError("prepared rating tables require exactly one export row")
    metadata = {
        str(key): _sql_value(value) for key, value in tables.export_frame.iloc[0].to_dict().items()
    }
    build = prepared.build
    requested = {
        "export_id": build.export_id,
        "model_name": prepared.model_config.model_name,
        "model_version": build.model_version,
        "effective_from_date": build.effective_from,
        "effective_to_date": prepared.effective_to,
        "source_file": str(Path(build.rating_workbook_path).resolve()),
        "publication_receipt_sha256": build.publication_receipt_sha256,
    }
    fields = tuple(requested)
    conflicts = immutable_conflicts(stored=metadata, requested=requested, fields=fields)
    if conflicts:
        details = "; ".join(
            f"{field} prepared={metadata.get(field)!r} requested={requested[field]!r}"
            for field in conflicts
        )
        raise ValueError(
            f"export_id {build.export_id!r} has incompatible prepared evidence: {details}"
        )
    return metadata


def _validate_prepared(
    prepared: PreparedPublication,
    tables: RatingTables,
) -> dict[str, object]:
    build = prepared.build
    mismatches = []
    for field_name, actual, expected in (
        ("model_name", build.model_name, prepared.model_config.model_name),
        ("model_type", build.model_type, prepared.model_config.model_type),
        ("target_name", build.target_name, prepared.model_config.target_name),
        ("deployment_slot", build.deployment_slot, prepared.model_config.deployment_slot),
    ):
        if actual != expected:
            mismatches.append(f"{field_name} build={actual!r} registered={expected!r}")
    if mismatches:
        raise ApprovedModelBuildError(
            "approved build does not match the registered model: " + "; ".join(mismatches)
        )
    if not str(build.manifest_id or "").strip():
        raise ApprovedModelBuildError("local notebook publication requires an existing manifest_id")
    if not str(build.export_id or "").strip():
        raise ApprovedModelBuildError("local notebook publication requires an export_id")
    for field_name, digest in (
        ("staging_content_sha256", tables.staging_content_sha256),
        ("model_equivalence_sha256", tables.model_equivalence_sha256),
    ):
        if _SHA256_RE.fullmatch(str(digest)) is None:
            raise ApprovedModelBuildError(f"prepared rating tables have invalid {field_name}")
    if build.model_equivalence_sha256 is None:
        raise ApprovedModelBuildError("local publication requires model_equivalence_sha256")
    if build.model_equivalence_sha256 != tables.model_equivalence_sha256:
        raise ApprovedModelBuildError(
            "prepared model equivalence digest does not match the completed build"
        )
    return _export_metadata(prepared, tables)


def _existing_local_publication(
    connection: Connection,
    *,
    model_id: int,
    export_id: str,
):
    return (
        connection.execute(
            text(
                """
                SELECT
                    rp.rate_package_id,
                    rp.package_version,
                    rp.package_status,
                    rp.model_version,
                    rp.manifest_id,
                    rp.split_set_id,
                    rp.rating_workbook_path,
                    rp.publication_receipt_sha256,
                    rp.staging_content_sha256,
                    rp.source_export_id,
                    rp.effective_from_date,
                    rp.effective_to_date,
                    rp.parent_rate_package_id,
                    rp.revision_metadata_json,
                    mr.model_run_id,
                    mr.run_status,
                    mr.dag_id,
                    mr.model_kind,
                    mr.model_equivalence_sha256,
                    mr.rating_workbook_sha256,
                    mr.airflow_run_id,
                    mr.mlflow_run_id,
                    mr.publication_receipt_path,
                    mr.model_artifact_path,
                    mr.candidate_artifact_path,
                    mr.candidate_artifact_sha256,
                    mr.candidate_artifact_format,
                    mr.candidate_artifact_size_bytes,
                    mr.candidate_python_version,
                    mr.candidate_superglm_version,
                    mr.model_source_sha256,
                    mr.parent_model_run_id,
                    mr.effective_from
                FROM pricing.PRICING_RATE_PACKAGE AS rp
                LEFT JOIN pricing.MODEL_RUN AS mr
                  ON mr.rate_package_id = rp.rate_package_id
                WHERE rp.model_id = :model_id
                  AND rp.source_export_id = :export_id
                """
            ),
            {"model_id": model_id, "export_id": export_id},
        )
        .mappings()
        .one_or_none()
    )


def _validate_existing_lineage_links(
    connection: Connection,
    *,
    model_run_id: object,
    manifest_id: str,
    split_set_id: str | None,
) -> None:
    dataset_links = set(
        connection.execute(
            text(
                "SELECT manifest_id, dataset_role FROM mlops.MODEL_RUN_DATASET "
                "WHERE model_run_id = :model_run_id"
            ),
            {"model_run_id": model_run_id},
        ).all()
    )
    split_links = set(
        connection.execute(
            text(
                "SELECT manifest_id, split_set_id, dataset_role, split_role "
                "FROM mlops.MODEL_RUN_SPLIT_SET WHERE model_run_id = :model_run_id"
            ),
            {"model_run_id": model_run_id},
        ).all()
    )
    expected_splits = (
        set() if split_set_id is None else {(manifest_id, split_set_id, "training", "validation")}
    )
    if dataset_links != {(manifest_id, "training")} or split_links != expected_splits:
        raise RuntimeError(
            "incomplete local publication lineage: dataset/split links do not "
            "match the immutable model run"
        )


def _model_run_evidence_conflicts(
    connection: Connection,
    existing: Mapping[str, object],
    *,
    prepared: PreparedPublication,
) -> list[str]:
    build = prepared.build
    model_run_id = existing["model_run_id"]
    if model_run_id is None:
        raise RuntimeError(
            f"incomplete local publication lineage: export {build.export_id!r} has no model run"
        )
    if str(existing["run_status"] or "").upper() != "SUCCESS":
        raise RuntimeError(
            f"incomplete local publication lineage: export {build.export_id!r} "
            "has no successful model run"
        )
    _validate_existing_lineage_links(
        connection,
        model_run_id=model_run_id,
        manifest_id=build.manifest_id,
        split_set_id=build.split_set_id,
    )
    requested = {
        "dag_id": prepared.execution_name,
        "airflow_run_id": prepared.execution_id,
        "model_kind": build.model_kind,
        "model_equivalence_sha256": build.model_equivalence_sha256,
        "mlflow_run_id": build.mlflow_run_id,
        "publication_receipt_path": build.publication_receipt_path,
        "publication_receipt_sha256": build.publication_receipt_sha256,
        "model_artifact_path": None,
        "candidate_artifact_path": build.candidate_artifact_path,
        "candidate_artifact_sha256": build.candidate_artifact_sha256,
        "candidate_artifact_format": build.candidate_artifact_format,
        "candidate_artifact_size_bytes": build.candidate_artifact_size_bytes,
        "candidate_python_version": build.candidate_python_version,
        "candidate_superglm_version": build.candidate_superglm_version,
        "model_source_sha256": build.model_source_sha256,
        "parent_model_run_id": prepared.parent_model_run_id,
        "effective_from": build.effective_from,
    }
    conflicts = [
        f"{field} existing={existing[field]!r} requested={requested[field]!r}"
        for field in immutable_conflicts(
            stored=existing,
            requested=requested,
            fields=tuple(requested),
        )
    ]
    stored_metrics = {
        str(row[0]): (float(row[1]), _identity(row[2]))
        for row in connection.execute(
            text(
                "SELECT metric_name, metric_value, metric_scope "
                "FROM mlops.MODEL_RUN_METRIC WHERE model_run_id = :model_run_id"
            ),
            {"model_run_id": model_run_id},
        ).all()
    }
    requested_metrics = {
        str(name): (float(value), _identity(build.metric_scopes.get(name, "model_run")))
        for name, value in build.metrics.items()
    }
    if stored_metrics != requested_metrics:
        conflicts.append(f"metrics existing={stored_metrics!r} requested={requested_metrics!r}")
    stored_folds = {
        (int(row[0]), str(row[1]), float(row[2]))
        for row in connection.execute(
            text(
                "SELECT fold_no, metric_name, metric_value "
                "FROM pricing.CV_FOLD_METRIC WHERE model_run_id = :model_run_id"
            ),
            {"model_run_id": model_run_id},
        ).all()
    }
    requested_folds = {
        (int(metric["fold_no"]), str(metric["metric_name"]), float(metric["metric_value"]))
        for metric in build.fold_metrics
    }
    if stored_folds != requested_folds:
        conflicts.append(f"fold_metrics existing={stored_folds!r} requested={requested_folds!r}")
    return conflicts


def _local_publication_conflicts(
    existing: Mapping[str, object],
    *,
    prepared: PreparedPublication,
    tables: RatingTables,
) -> list[str]:
    build = prepared.build
    requested = {
        "model_version": build.model_version,
        "manifest_id": build.manifest_id,
        "split_set_id": build.split_set_id,
        "effective_from_date": build.effective_from,
        "effective_to_date": prepared.effective_to,
        "parent_rate_package_id": prepared.parent_rate_package_id,
        "revision_metadata_json": canonical_revision_metadata(prepared.revision_metadata),
        "rating_workbook_path": build.rating_workbook_path,
        "rating_workbook_sha256": build.rating_workbook_sha256,
        "publication_receipt_sha256": build.publication_receipt_sha256,
        "model_equivalence_sha256": build.model_equivalence_sha256,
    }
    conflicts = [
        f"{field} existing={existing[field]!r} requested={requested[field]!r}"
        for field in immutable_conflicts(
            stored=existing,
            requested=requested,
            fields=tuple(requested),
        )
    ]
    if _identity(existing["staging_content_sha256"]) != tables.staging_content_sha256:
        conflicts.append(
            "staging_content_sha256 "
            f"existing={existing['staging_content_sha256']!r} "
            f"requested={tables.staging_content_sha256!r}"
        )
    return conflicts


def _require_stored_digests(package_row: Mapping[str, object]) -> None:
    for field_name in (
        "staging_content_sha256",
        "model_equivalence_sha256",
        "rating_workbook_sha256",
        "publication_receipt_sha256",
        "candidate_artifact_sha256",
        "model_source_sha256",
    ):
        if _SHA256_RE.fullmatch(str(package_row[field_name] or "")) is None:
            raise ApprovedModelBuildError(
                f"equivalent local publication is missing required {field_name}"
            )


def _equivalent_local_publication(
    connection: Connection,
    prepared: PreparedPublication,
):
    build = prepared.build
    rows = (
        connection.execute(
            text(
                """
                SELECT mr.model_run_id, rp.rate_package_id, rp.source_export_id,
                       rp.package_status, rp.effective_from_date
                FROM pricing.MODEL_RUN AS mr
                JOIN pricing.PRICING_RATE_PACKAGE AS rp
                  ON rp.rate_package_id = mr.rate_package_id
                WHERE mr.model_id = :model_id
                  AND mr.manifest_id = :manifest_id
                  AND mr.model_kind = :model_kind
                  AND mr.model_equivalence_sha256 = :model_equivalence_sha256
                  AND mr.run_status = 'SUCCESS'
                """
            ),
            {
                "model_id": build.model_id,
                "manifest_id": build.manifest_id,
                "model_kind": build.model_kind,
                "model_equivalence_sha256": build.model_equivalence_sha256,
            },
        )
        .mappings()
        .all()
    )
    if len(rows) > 1:
        raise ModelEquivalenceError(
            "equivalent rating fingerprint resolves multiple successful model runs"
        )
    if not rows:
        return None
    row = rows[0]
    if _date_identity(row["effective_from_date"]) != _date_identity(build.effective_from):
        raise ModelEquivalenceError(
            "an equivalent model build already exists under a different "
            "effective_from date; the current schema cannot preserve a new release intent "
            "without separating model builds from rate packages"
        )
    training_links = connection.execute(
        text(
            "SELECT COUNT(*) FROM mlops.MODEL_RUN_DATASET "
            "WHERE model_run_id = :model_run_id AND manifest_id = :manifest_id "
            "AND dataset_role = 'training'"
        ),
        {"model_run_id": row["model_run_id"], "manifest_id": build.manifest_id},
    ).scalar_one()
    if int(training_links) != 1:
        raise ModelEquivalenceError(
            "equivalent model run does not have exactly one matching training-manifest link"
        )
    split_links = connection.execute(
        text(
            "SELECT manifest_id, split_set_id FROM mlops.MODEL_RUN_SPLIT_SET "
            "WHERE model_run_id = :model_run_id AND dataset_role = 'training' "
            "AND split_role = 'validation'"
        ),
        {"model_run_id": row["model_run_id"]},
    ).all()
    if len(split_links) > 1:
        raise ModelEquivalenceError(
            "equivalent model run resolves multiple training/validation split links"
        )
    if split_links and str(split_links[0][0]) != build.manifest_id:
        raise ModelEquivalenceError(
            "equivalent model run split lineage points at a different manifest"
        )
    if str(row["package_status"]).upper() != "LOCAL_AUDIT":
        raise ApprovedModelBuildError(
            f"equivalent local model package has unusable status {row['package_status']!r}"
        )
    return _existing_local_publication(
        connection,
        model_id=build.model_id,
        export_id=str(row["source_export_id"]),
    )


def _resolve_existing_or_equivalent(
    connection: Connection,
    prepared: PreparedPublication,
    tables: RatingTables,
) -> CompletedModelPublishResult | None:
    build = prepared.build
    existing = _existing_local_publication(
        connection,
        model_id=build.model_id,
        export_id=build.export_id,
    )
    if existing is not None:
        conflicts = _local_publication_conflicts(
            existing,
            prepared=prepared,
            tables=tables,
        )
        if conflicts:
            raise ValueError(
                f"export_id {build.export_id!r} has incompatible publication evidence: "
                + "; ".join(conflicts)
            )
        run_conflicts = _model_run_evidence_conflicts(
            connection,
            existing,
            prepared=prepared,
        )
        if run_conflicts:
            raise ValueError(
                f"export_id {build.export_id!r} has incompatible model-run evidence: "
                + "; ".join(run_conflicts)
            )
        return _publication_result(existing, prepared, was_existing=True)

    equivalent = _equivalent_local_publication(connection, prepared)
    if equivalent is None:
        return None
    _require_stored_digests(equivalent)
    connection.execute(
        text(
            "DELETE FROM pricing.PRICING_MODEL_VERSION_RESERVATION "
            "WHERE model_id = :model_id AND export_id = :export_id"
        ),
        {"model_id": build.model_id, "export_id": build.export_id},
    )
    return _publication_result(
        equivalent,
        prepared,
        was_existing=True,
        deduplicated=True,
    )


def _require_reserved_version(
    connection: Connection,
    prepared: PreparedPublication,
) -> None:
    build = prepared.build
    reserved_version = connection.execute(
        text(
            "SELECT model_version FROM pricing.PRICING_MODEL_VERSION_RESERVATION "
            "WHERE model_id = :model_id AND export_id = :export_id"
        ),
        {"model_id": build.model_id, "export_id": build.export_id},
    ).scalar_one_or_none()
    if reserved_version is None:
        raise ApprovedModelBuildError(
            f"local export {build.export_id!r} has no reserved model version; "
            "build it through build_candidate before publication"
        )
    if str(reserved_version) != build.model_version:
        raise ApprovedModelBuildError(
            f"local export {build.export_id!r} reserved model version "
            f"{reserved_version!r}, not {build.model_version!r}"
        )
    manifest_exists = connection.execute(
        text("SELECT 1 FROM pricing.DATASET_MANIFEST WHERE manifest_id = :manifest_id"),
        {"manifest_id": build.manifest_id},
    ).scalar_one_or_none()
    if manifest_exists is None:
        raise ApprovedModelBuildError(f"local manifest_id {build.manifest_id!r} does not exist")
    if build.split_set_id is not None:
        split_exists = connection.execute(
            text(
                "SELECT 1 FROM pricing.CV_SPLIT_SET WHERE split_set_id = :split_set_id "
                "AND manifest_id = :manifest_id"
            ),
            {"split_set_id": build.split_set_id, "manifest_id": build.manifest_id},
        ).scalar_one_or_none()
        if split_exists is None:
            raise ApprovedModelBuildError(
                f"local split_set_id {build.split_set_id!r} does not match the manifest"
            )


def _insert_local_package(
    connection: Connection,
    prepared: PreparedPublication,
    tables: RatingTables,
    metadata: Mapping[str, object],
):
    build = prepared.build
    package_version = int(
        connection.execute(
            text(
                "SELECT COALESCE(MAX(package_version), 0) + 1 "
                "FROM pricing.PRICING_RATE_PACKAGE WHERE model_id = :model_id"
            ),
            {"model_id": build.model_id},
        ).scalar_one()
    )
    inserted = connection.execute(
        text(
            """
            INSERT INTO pricing.PRICING_RATE_PACKAGE (
                parent_rate_package_id, model_id, model_name, model_version,
                package_version, base_rate, effective_from_date, effective_to_date,
                package_status, source_export_id, source_file,
                publication_receipt_json, publication_receipt_sha256,
                staging_content_sha256, package_metadata_json, offset_handling,
                revision_metadata_json,
                offset_factor_name, offset_source_name, offset_label, metadata_origin,
                manifest_id, split_set_id, rating_workbook_path, model_artifact_path,
                created_by
            ) VALUES (
                :parent_rate_package_id, :model_id, :model_name, :model_version,
                :package_version, :base_rate, :effective_from_date, :effective_to_date,
                'LOCAL_AUDIT', :source_export_id, :source_file,
                :publication_receipt_json, :publication_receipt_sha256,
                :staging_content_sha256, :package_metadata_json, :offset_handling,
                :revision_metadata_json,
                :offset_factor_name, :offset_source_name, :offset_label, :metadata_origin,
                :manifest_id, :split_set_id, :rating_workbook_path, NULL, :created_by
            )
            """
        ),
        {
            "parent_rate_package_id": prepared.parent_rate_package_id,
            "model_id": build.model_id,
            "model_name": prepared.model_config.model_name,
            "model_version": build.model_version,
            "package_version": package_version,
            "base_rate": metadata["base_rate"],
            "effective_from_date": metadata.get("effective_from_date"),
            "effective_to_date": metadata.get("effective_to_date"),
            "source_export_id": build.export_id,
            "source_file": metadata.get("source_file"),
            "publication_receipt_json": metadata.get("publication_receipt_json"),
            "publication_receipt_sha256": metadata.get("publication_receipt_sha256"),
            "staging_content_sha256": tables.staging_content_sha256,
            "package_metadata_json": metadata.get("package_metadata_json"),
            "offset_handling": metadata.get("offset_handling") or "UNKNOWN",
            "revision_metadata_json": canonical_revision_metadata(prepared.revision_metadata),
            "offset_factor_name": metadata.get("offset_factor_name"),
            "offset_source_name": metadata.get("offset_source_name"),
            "offset_label": metadata.get("offset_label"),
            "metadata_origin": metadata.get("metadata_origin"),
            "manifest_id": build.manifest_id,
            "split_set_id": build.split_set_id,
            "rating_workbook_path": build.rating_workbook_path,
            "created_by": build.created_by,
        },
    )
    return {
        "rate_package_id": int(inserted.lastrowid),
        "package_version": package_version,
    }


def _insert_local_rating_tables(
    connection: Connection,
    package: Mapping[str, int],
    tables: RatingTables,
) -> None:
    if tables.rate_cells.empty:
        return
    metadata_by_term = {
        str(row["term_name"]): _sql_value(row["term_metadata_json"])
        for row in tables.term_metadata.to_dict("records")
    }
    rate_package_id = package["rate_package_id"]
    grouped = tables.rate_cells.groupby(
        ["term_name", "term_type", "sequence_no"],
        sort=True,
        dropna=False,
    )
    for (term_name, term_type, sequence_no), cells in grouped:
        term_insert = connection.execute(
            text(
                """
                INSERT INTO pricing.PRICING_TERM (
                    rate_package_id, term_name, term_type, sequence_no,
                    default_multiplier, default_log_coefficient,
                    term_metadata_json, active_flag
                ) VALUES (
                    :rate_package_id, :term_name, :term_type, :sequence_no,
                    1.0, 0.0, :term_metadata_json, 1
                )
                """
            ),
            {
                "rate_package_id": rate_package_id,
                "term_name": str(term_name),
                "term_type": str(term_type),
                "sequence_no": int(sequence_no),
                "term_metadata_json": metadata_by_term.get(str(term_name)),
            },
        )
        term_id = int(term_insert.lastrowid)
        rows = []
        for cell in cells.sort_values("row_id").to_dict("records"):
            cell_key = str(cell["cell_key_text"])
            rows.append(
                {
                    "rate_package_id": rate_package_id,
                    "term_id": term_id,
                    "cell_key_digest": hashlib.sha256(cell_key.encode("utf-8")).hexdigest(),
                    "term_name": str(term_name),
                    "term_type": str(term_type),
                    "sequence_no": int(sequence_no),
                    "cell_key_text": cell_key,
                    "multiplier": float(cell["multiplier"]),
                    "log_coefficient": float(cell["log_coefficient"]),
                    "exposure_weight": _sql_value(cell.get("exposure_weight")),
                    "record_count": _sql_value(cell.get("record_count")),
                    "is_default": int(cell["is_default"]),
                    "is_reference": int(cell["is_reference"]),
                }
            )
        connection.execute(
            text(
                """
                INSERT INTO pricing.PRICING_COMPILED_RATE_CELL (
                    rate_package_id, term_id, cell_key_digest, term_name, term_type,
                    sequence_no, cell_key_text, multiplier, log_coefficient,
                    exposure_weight, record_count, is_default, is_reference
                ) VALUES (
                    :rate_package_id, :term_id, :cell_key_digest, :term_name, :term_type,
                    :sequence_no, :cell_key_text, :multiplier, :log_coefficient,
                    :exposure_weight, :record_count, :is_default, :is_reference
                )
                """
            ),
            rows,
        )


def _insert_local_lineage(
    connection: Connection,
    package: Mapping[str, int],
    prepared: PreparedPublication,
) -> int:
    build = prepared.build
    model_run_id = package["rate_package_id"]
    connection.execute(
        text(
            """
            INSERT INTO pricing.MODEL_RUN (
                model_run_id, parent_model_run_id, model_id, dag_id, airflow_run_id,
                mlflow_run_id, model_version, model_kind, model_equivalence_sha256,
                export_id, manifest_id, split_set_id, rate_package_id, model_name,
                rating_workbook_path, rating_workbook_sha256,
                publication_receipt_path, publication_receipt_sha256,
                model_artifact_path, candidate_artifact_path, candidate_artifact_sha256,
                candidate_artifact_format, candidate_artifact_size_bytes,
                candidate_python_version, candidate_superglm_version,
                model_source_sha256, effective_from, run_status, completed_ts, created_by
            ) VALUES (
                :model_run_id, :parent_model_run_id, :model_id, :dag_id, :airflow_run_id,
                :mlflow_run_id, :model_version, :model_kind, :model_equivalence_sha256,
                :export_id, :manifest_id, :split_set_id, :rate_package_id, :model_name,
                :rating_workbook_path, :rating_workbook_sha256,
                :publication_receipt_path, :publication_receipt_sha256,
                NULL, :candidate_artifact_path, :candidate_artifact_sha256,
                :candidate_artifact_format, :candidate_artifact_size_bytes,
                :candidate_python_version, :candidate_superglm_version,
                :model_source_sha256, :effective_from, 'SUCCESS', CURRENT_TIMESTAMP, :created_by
            )
            """
        ),
        {
            "model_run_id": model_run_id,
            "parent_model_run_id": prepared.parent_model_run_id,
            "model_id": build.model_id,
            "dag_id": prepared.execution_name,
            "airflow_run_id": prepared.execution_id,
            "mlflow_run_id": build.mlflow_run_id,
            "model_version": build.model_version,
            "model_kind": build.model_kind,
            "model_equivalence_sha256": build.model_equivalence_sha256,
            "export_id": build.export_id,
            "manifest_id": build.manifest_id,
            "split_set_id": build.split_set_id,
            "rate_package_id": package["rate_package_id"],
            "model_name": prepared.model_config.model_name,
            "rating_workbook_path": build.rating_workbook_path,
            "rating_workbook_sha256": build.rating_workbook_sha256,
            "publication_receipt_path": build.publication_receipt_path,
            "publication_receipt_sha256": build.publication_receipt_sha256,
            "candidate_artifact_path": build.candidate_artifact_path,
            "candidate_artifact_sha256": build.candidate_artifact_sha256,
            "candidate_artifact_format": build.candidate_artifact_format,
            "candidate_artifact_size_bytes": build.candidate_artifact_size_bytes,
            "candidate_python_version": build.candidate_python_version,
            "candidate_superglm_version": build.candidate_superglm_version,
            "model_source_sha256": build.model_source_sha256,
            "effective_from": build.effective_from,
            "created_by": build.created_by,
        },
    )
    connection.execute(
        text(
            "INSERT INTO mlops.MODEL_RUN_DATASET "
            "(model_run_id, manifest_id, dataset_role) "
            "VALUES (:model_run_id, :manifest_id, 'training')"
        ),
        {"model_run_id": model_run_id, "manifest_id": build.manifest_id},
    )
    if build.split_set_id is not None:
        connection.execute(
            text(
                "INSERT INTO mlops.MODEL_RUN_SPLIT_SET "
                "(model_run_id, manifest_id, split_set_id, dataset_role, split_role) "
                "VALUES (:model_run_id, :manifest_id, :split_set_id, "
                "'training', 'validation')"
            ),
            {
                "model_run_id": model_run_id,
                "manifest_id": build.manifest_id,
                "split_set_id": build.split_set_id,
            },
        )
    for metric_name, metric_value in sorted(build.metrics.items()):
        connection.execute(
            text(
                "INSERT INTO mlops.MODEL_RUN_METRIC "
                "(model_run_id, metric_name, metric_value, metric_scope) "
                "VALUES (:model_run_id, :metric_name, :metric_value, :metric_scope)"
            ),
            {
                "model_run_id": model_run_id,
                "metric_name": metric_name,
                "metric_value": float(metric_value),
                "metric_scope": build.metric_scopes.get(metric_name, "model_run"),
            },
        )
    if build.fold_metrics and build.split_set_id is None:
        raise ApprovedModelBuildError(
            "fold metrics require split_set_id in local notebook publication"
        )
    for metric in build.fold_metrics:
        connection.execute(
            text(
                "INSERT INTO pricing.CV_FOLD_METRIC "
                "(model_run_id, split_set_id, fold_no, metric_name, metric_value) "
                "VALUES (:model_run_id, :split_set_id, :fold_no, :metric_name, :metric_value)"
            ),
            {
                "model_run_id": model_run_id,
                "split_set_id": build.split_set_id,
                "fold_no": int(metric["fold_no"]),
                "metric_name": str(metric["metric_name"]),
                "metric_value": float(metric["metric_value"]),
            },
        )
    return model_run_id


def _publication_result(
    package_row: Mapping[str, object],
    prepared: PreparedPublication,
    *,
    was_existing: bool,
    deduplicated: bool = False,
) -> CompletedModelPublishResult:
    model_run_id = package_row["model_run_id"]
    if model_run_id is None:
        raise RuntimeError(
            f"Local export {package_row['source_export_id']!r} has a package "
            "without model-run audit rows"
        )
    return CompletedModelPublishResult(
        model_id=prepared.build.model_id,
        model_name=prepared.model_config.model_name,
        model_version=str(package_row["model_version"]),
        manifest_id=str(package_row["manifest_id"]),
        split_set_id=(
            None if package_row["split_set_id"] is None else str(package_row["split_set_id"])
        ),
        export_id=str(package_row["source_export_id"]),
        rate_package_id=int(package_row["rate_package_id"]),
        package_version=int(package_row["package_version"]),
        package_status=str(package_row["package_status"]),
        rating_workbook_path=str(package_row["rating_workbook_path"]),
        model_run_id=int(model_run_id),
        mlflow_run_id=_identity(package_row["mlflow_run_id"]),
        publication_receipt_path=_identity(package_row["publication_receipt_path"]),
        publication_receipt_sha256=_identity(package_row["publication_receipt_sha256"]),
        was_existing=was_existing,
        deduplicated=deduplicated,
        model_kind=str(package_row["model_kind"]),
        model_equivalence_sha256=str(package_row["model_equivalence_sha256"]),
    )


def publish_sqlite(
    engine: Engine,
    prepared: PreparedPublication,
    tables: RatingTables,
) -> CompletedModelPublishResult:
    """Publish one prepared local candidate atomically without SQLite staging."""
    metadata = _validate_prepared(prepared, tables)
    with _sqlite_publication_transaction(engine, prepared) as connection:
        existing = _resolve_existing_or_equivalent(connection, prepared, tables)
        if existing is not None:
            return existing
        _require_reserved_version(connection, prepared)
        package = _insert_local_package(connection, prepared, tables, metadata)
        _insert_local_rating_tables(connection, package, tables)
        _insert_local_lineage(connection, package, prepared)
        created = _existing_local_publication(
            connection,
            model_id=prepared.build.model_id,
            export_id=prepared.build.export_id,
        )
        if created is None:
            raise RuntimeError("Local publication was not visible after insert")
        return _publication_result(created, prepared, was_existing=False)


__all__ = ["publish_sqlite"]
