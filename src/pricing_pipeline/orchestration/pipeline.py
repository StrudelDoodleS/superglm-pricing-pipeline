from __future__ import annotations

from pathlib import Path

from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.publish import (
    CompletedModelPublishResult,
    ModelRegistryError,
    PublicationRequest,
    publish_candidate,
)
from pricing_pipeline.publishing.sqlserver import validate_registered_model
from pricing_pipeline.workbench.submission import sha256_file


class PublishedRunIntegrityError(RuntimeError):
    """Raised when an approved export's immutable workbook evidence cannot be verified."""


def publish_model_export(
    engine,
    export: ApprovedModelBuild,
    *,
    model_config: ModelBuildConfig,
    validated_model_id: int | None = None,
    allowed_artifact_root: str | Path | None = None,
) -> CompletedModelPublishResult:
    workbook_path = Path(export.rating_workbook_path)
    if not workbook_path.is_file():
        raise PublishedRunIntegrityError(
            f"rating workbook does not exist: {workbook_path.as_posix()}"
        )
    actual_workbook_sha256 = sha256_file(workbook_path)
    if actual_workbook_sha256 != export.rating_workbook_sha256:
        raise PublishedRunIntegrityError(
            "rating workbook SHA-256 does not match the export evidence: "
            f"expected={export.rating_workbook_sha256!r}, actual={actual_workbook_sha256!r}"
        )
    if validated_model_id is None:
        with engine.begin() as connection:
            model_id = validate_registered_model(connection, model_config).model_id
    else:
        model_id = int(validated_model_id)
    _validate_export_matches_config(export, model_config, model_id=model_id)
    request = PublicationRequest(
        build=export,
        model_config=model_config,
        execution_name="notebook",
        execution_id=export.export_id,
        allowed_artifact_root=(
            None if allowed_artifact_root is None else Path(allowed_artifact_root)
        ),
    )
    return publish_candidate(engine, request)


def _validate_export_matches_config(
    export: ApprovedModelBuild,
    config: ModelBuildConfig,
    *,
    model_id: int,
) -> None:
    mismatches = []
    for field_name, actual, expected in (
        ("model_id", int(export.model_id), int(model_id)),
        ("model_name", export.model_name, config.model_name),
        ("target_name", export.target_name, config.target_name),
        ("model_type", export.model_type, config.model_type),
        ("deployment_slot", export.deployment_slot, config.deployment_slot),
    ):
        if actual != expected:
            mismatches.append(f"{field_name} export={actual!r} config={expected!r}")
    if mismatches:
        raise ModelRegistryError(
            "training export does not match model config: " + "; ".join(mismatches)
        )
