"""Temporary notebook compatibility forwards for concrete SQLite publication."""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import text

from pricing_pipeline.infra.config import Settings
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild, ApprovedModelBuildError
from pricing_pipeline.orchestration.publish_completed_build import (
    CompletedModelPublishResult,
    _verify_candidate_artifact,
    load_candidate_sql_lineage,
)
from pricing_pipeline.publishing.model_registry import (
    PricingModelRecord,
    validate_registered_model,
)
from pricing_pipeline.publishing.publish import (
    PublicationRequest,
    publish_candidate,
)
from pricing_pipeline.workbench.submission import sha256_file

_VERSION_PATTERN = re.compile(r"^v([0-9]+)$")


def register_sqlite_model(
    engine,
    config: ModelBuildConfig,
    *,
    created_by: str,
) -> PricingModelRecord:
    """Insert once and validate the complete stable model identity."""
    params = {
        "model_name": config.model_name,
        "model_label": config.model_label,
        "target_name": config.target_name,
        "model_type": config.model_type,
        "created_by": created_by,
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO pricing.PRICING_MODEL (
                    model_name, model_label, target_name, model_type,
                    model_status, created_by
                ) VALUES (
                    :model_name, :model_label, :target_name, :model_type,
                    'ACTIVE', :created_by
                )
                """
            ),
            params,
        )
        return validate_registered_model(connection, config)


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
            existing = connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM pricing.PRICING_RATE_PACKAGE
                    WHERE model_id = :model_id AND source_export_id = :export_id
                    UNION ALL
                    SELECT model_version
                    FROM pricing.PRICING_MODEL_VERSION_RESERVATION
                    WHERE model_id = :model_id AND export_id = :export_id
                    LIMIT 1
                    """
                ),
                {"model_id": model_id, "export_id": export_id},
            ).scalar_one_or_none()
            if existing is not None:
                connection.commit()
                return str(existing)

            versions = connection.execute(
                text(
                    """
                    SELECT model_version
                    FROM pricing.PRICING_RATE_PACKAGE
                    WHERE model_id = :model_id AND parent_rate_package_id IS NULL
                    UNION ALL
                    SELECT model_version
                    FROM pricing.PRICING_MODEL_VERSION_RESERVATION
                    WHERE model_id = :model_id
                    """
                ),
                {"model_id": model_id},
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
                    ) VALUES (
                        :model_id, :export_id, :model_version
                    )
                    """
                ),
                {
                    "model_id": model_id,
                    "export_id": export_id,
                    "model_version": reserved,
                },
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
    """Validate notebook evidence and forward one common publication request."""
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
    """Retain the transitional internal signature while using the common flow."""
    del created_by
    if not isinstance(completed_build, ApprovedModelBuild):
        raise TypeError("completed_build must be an ApprovedModelBuild")
    build = completed_build
    mismatches = []
    for field_name, actual, expected in (
        ("model_id", build.model_id, model_id),
        ("model_name", build.model_name, model_config.model_name),
        ("model_type", build.model_type, model_config.model_type),
        ("target_name", build.target_name, model_config.target_name),
        ("deployment_slot", build.deployment_slot, model_config.deployment_slot),
    ):
        if actual != expected:
            mismatches.append(f"{field_name} build={actual!r} registered={expected!r}")
    if mismatches:
        raise ApprovedModelBuildError(
            "approved build does not match the registered model: " + "; ".join(mismatches)
        )
    workbook_path = Path(build.rating_workbook_path)
    if not workbook_path.is_file():
        raise ApprovedModelBuildError(
            f"rating_workbook_path does not exist: {workbook_path.as_posix()}"
        )
    actual_workbook_sha256 = sha256_file(workbook_path)
    if actual_workbook_sha256 != build.rating_workbook_sha256:
        raise ApprovedModelBuildError(
            "rating workbook SHA-256 does not match the completed build: "
            f"expected={build.rating_workbook_sha256!r}, actual={actual_workbook_sha256!r}"
        )
    manifest_id = str(build.manifest_id or "").strip()
    if not manifest_id:
        raise ApprovedModelBuildError("local notebook publication requires an existing manifest_id")
    export_id = str(build.export_id or "").strip()
    if not export_id:
        raise ApprovedModelBuildError("local notebook publication requires an export_id")
    if build.candidate_artifact_path is not None:
        sql_lineage = load_candidate_sql_lineage(
            engine,
            manifest_id=manifest_id,
            split_set_id=build.split_set_id,
        )
        _verify_candidate_artifact(
            build,
            sql_lineage=sql_lineage,
            allowed_root=artifact_root,
        )
    request = PublicationRequest(
        build=build,
        model_config=model_config,
        execution_name="notebook_local",
        execution_id=export_id,
        allowed_artifact_root=Path(artifact_root),
    )
    return publish_candidate(engine, request)


__all__ = [
    "publish_sqlite_candidate",
    "register_sqlite_model",
    "resolve_sqlite_model_version",
]
