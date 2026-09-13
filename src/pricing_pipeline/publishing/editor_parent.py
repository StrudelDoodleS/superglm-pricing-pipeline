"""Load and verify an editor submission's saved parent and deployed comparison model.

Bind SQL lineage to candidate artifacts and recipe capture before returning
ParentCandidate to the publication workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.recipes import RecipeError
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.publishing.editor_contracts import ChampionSnapshot, ParentCandidate
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
)
from pricing_pipeline.publishing.recipes import validate_recipe_capture
from pricing_pipeline.workbench.artifacts import (
    CandidateArtifactError,
    CandidateBundle,
    load_candidate_bundle,
)
from pricing_pipeline.workbench.submission import (
    EditorSubmission,
    EditorSubmissionError,
)


def _verify_model_frame_sha256(
    bundle: CandidateBundle,
    sql_digest: Any,
    *,
    context: str,
) -> None:
    if (
        not isinstance(sql_digest, str)
        or len(sql_digest) != 64
        or any(character not in "0123456789abcdef" for character in sql_digest)
    ):
        raise EditorSubmissionError(
            f"{context} SQL manifest model_frame_sha256 is missing or invalid"
        )
    if bundle.model_frame_sha256 is None:
        raise EditorSubmissionError(f"{context} bundle model_frame_sha256 is missing")
    if bundle.model_frame_sha256 != sql_digest:
        raise EditorSubmissionError(
            f"{context} bundle model_frame_sha256 does not match the SQL manifest"
        )


def load_parent_candidate(
    engine,
    submission: EditorSubmission,
    *,
    allowed_root: str | Path,
    model_config: ModelBuildConfig,
) -> ParentCandidate:
    submitted_slot = str(submission.deployment_slot or "").strip().upper()
    configured_slot = str(model_config.deployment_slot or "").strip().upper()
    if not submitted_slot or submitted_slot != configured_slot:
        raise EditorSubmissionError(
            "explicit model config deployment_slot does not match the editor submission"
        )

    schemas = schema_names_from_connectable(engine)
    query = text(
        f"""
        SELECT
            pm.model_id,
            pm.model_name,
            rp.model_version,
            rp.package_version,
            rp.rate_package_id,
            rp.package_status,
            rp.effective_from_date,
            rp.effective_to_date,
            mr.model_run_id,
            mr.run_status,
            mr.model_version AS run_model_version,
            mr.export_id,
            mr.manifest_id,
            mr.recipe_status,
            recipe.recipe_sha256,
            recipe.recipe_json,
            recipe.recipe_format_version,
            manifest.model_frame_sha256,
            split_link.split_set_id,
            mr.candidate_artifact_path,
            mr.candidate_artifact_sha256,
            mr.candidate_artifact_format,
            mr.candidate_artifact_size_bytes,
            mr.candidate_python_version,
            mr.candidate_superglm_version,
            mr.model_source_sha256
        FROM {schemas.pricing}.PRICING_RATE_PACKAGE AS rp
        JOIN {schemas.pricing}.PRICING_MODEL AS pm
          ON pm.model_id = rp.model_id
        JOIN {schemas.pricing}.MODEL_RUN AS mr
          ON mr.rate_package_id = rp.rate_package_id
        LEFT JOIN {schemas.pricing}.MODEL_RECIPE AS recipe
          ON recipe.model_id = mr.model_id AND recipe.recipe_id = mr.recipe_id
        JOIN {schemas.pricing}.DATASET_MANIFEST AS manifest
          ON manifest.manifest_id = mr.manifest_id
        LEFT JOIN {schemas.mlops}.MODEL_RUN_SPLIT_SET AS split_link
          ON split_link.model_run_id = mr.model_run_id
         AND split_link.manifest_id = mr.manifest_id
         AND split_link.dataset_role = 'training'
         AND split_link.split_role = 'validation'
        WHERE rp.rate_package_id = :rate_package_id
          AND mr.model_run_id = :model_run_id
        """
    )
    with engine.begin() as connection:
        rows = list(
            connection.execute(
                query,
                {
                    "rate_package_id": submission.parent_rate_package_id,
                    "model_run_id": submission.parent_model_run_id,
                },
            )
            .mappings()
            .all()
        )
    if len(rows) != 1:
        raise EditorSubmissionError(
            f"parent package must resolve exactly one successful model run; found {len(rows)}"
        )
    row = dict(rows[0])
    if str(row.get("package_status") or "").upper() != "PUBLISHED":
        raise EditorSubmissionError("parent rate package must still be PUBLISHED")
    expected = {
        "model_name": submission.model_name,
        "run_model_version": row["model_version"],
        "package_version": submission.source_package_version,
        "rate_package_id": submission.parent_rate_package_id,
        "model_run_id": submission.parent_model_run_id,
        "manifest_id": submission.manifest_id,
        "split_set_id": submission.split_set_id,
        "candidate_artifact_sha256": submission.baseline_candidate_sha256,
        "model_source_sha256": submission.model_source_sha256,
    }
    mismatches = [name for name, value in expected.items() if str(row.get(name)) != str(value)]
    if str(row.get("run_status") or "").upper() != "SUCCESS":
        mismatches.append("run_status")
    if mismatches:
        raise EditorSubmissionError(
            "parent SQL lineage no longer matches the submission: " + ", ".join(mismatches)
        )

    bundle = load_candidate_bundle(
        row["candidate_artifact_path"],
        expected_sha256=row["candidate_artifact_sha256"],
        expected_size_bytes=int(row["candidate_artifact_size_bytes"]),
        expected_format=row["candidate_artifact_format"],
        expected_python_version=row["candidate_python_version"],
        expected_superglm_version=row["candidate_superglm_version"],
        allowed_root=allowed_root,
    )
    try:
        validate_recipe_capture(row, bundle.recipe_capture)
    except RecipeError as exc:
        raise EditorSubmissionError(
            f"parent candidate recipe does not match SQL lineage: {exc}"
        ) from exc
    for field_name, expected_value in (
        ("model_name", row["model_name"]),
        ("model_version", row["run_model_version"]),
        ("export_id", row["export_id"]),
        ("manifest_id", submission.manifest_id),
        ("split_set_id", submission.split_set_id),
        ("model_source_sha256", submission.model_source_sha256),
    ):
        if getattr(bundle, field_name) != expected_value:
            raise EditorSubmissionError(
                f"parent bundle {field_name} does not match SQL/submission lineage"
            )
    _verify_model_frame_sha256(
        bundle,
        row.get("model_frame_sha256"),
        context="parent candidate",
    )
    config = model_config
    configured_name = config.model_name
    if str(configured_name) != submission.model_name:
        raise EditorSubmissionError(
            "explicit model config does not match the editor submission model_name"
        )
    champion = _load_champion_bundle(
        engine,
        model_id=int(row["model_id"]),
        deployment_slot=submitted_slot,
        allowed_root=allowed_root,
        parent_bundle=bundle,
    )
    return ParentCandidate(
        model_id=int(row["model_id"]),
        model_name=str(row["model_name"]),
        model_version=str(row["model_version"]),
        package_version=int(row["package_version"]),
        rate_package_id=int(row["rate_package_id"]),
        model_run_id=int(row["model_run_id"]),
        effective_from=(
            None if row.get("effective_from_date") is None else str(row["effective_from_date"])
        ),
        effective_to=(
            None if row.get("effective_to_date") is None else str(row["effective_to_date"])
        ),
        config=config,
        bundle=bundle,
        champion=champion,
    )


def _load_champion_bundle(
    engine,
    *,
    model_id: int,
    deployment_slot: str,
    allowed_root: Path,
    parent_bundle: CandidateBundle,
) -> ChampionSnapshot:
    def unavailable(rate_package_id: int | None, reason: str) -> ChampionSnapshot:
        return ChampionSnapshot(
            deployment_slot=deployment_slot,
            rate_package_id=rate_package_id,
            bundle=None,
            unavailable_reason=reason,
        )

    schemas = schema_names_from_connectable(engine)
    query = text(
        f"""
        SELECT
            deployment.rate_package_id,
            mr.run_status,
            mr.candidate_artifact_path,
            mr.candidate_artifact_sha256,
            mr.candidate_artifact_format,
            mr.candidate_artifact_size_bytes,
            mr.candidate_python_version,
            mr.candidate_superglm_version
        FROM {schemas.pricing}.PRICING_MODEL_DEPLOYMENT AS deployment
        LEFT JOIN {schemas.pricing}.MODEL_RUN AS mr
          ON mr.rate_package_id = deployment.rate_package_id
        WHERE deployment.model_id = :model_id
          AND deployment.deployment_slot = :deployment_slot
          AND deployment.effective_to_ts IS NULL
        """
    )
    with engine.begin() as connection:
        rows = list(
            connection.execute(
                query,
                {"model_id": model_id, "deployment_slot": deployment_slot},
            )
            .mappings()
            .all()
        )
    if not rows:
        return unavailable(None, f"no champion is deployed in {deployment_slot}")
    if len(rows) != 1:
        raise EditorSubmissionError(
            f"{len(rows)} current champion runs resolved in {deployment_slot}; "
            "comparison identity is ambiguous"
        )
    row = dict(rows[0])
    rate_package_id = int(row["rate_package_id"])
    if str(row.get("run_status") or "").upper() != "SUCCESS":
        return unavailable(rate_package_id, "the deployed champion has no successful candidate run")
    required = (
        "candidate_artifact_path",
        "candidate_artifact_sha256",
        "candidate_artifact_format",
        "candidate_artifact_size_bytes",
        "candidate_python_version",
        "candidate_superglm_version",
    )
    if any(row.get(name) is None for name in required):
        return unavailable(rate_package_id, "the deployed champion has no candidate artifact")
    try:
        champion = load_candidate_bundle(
            row["candidate_artifact_path"],
            expected_sha256=row["candidate_artifact_sha256"],
            expected_size_bytes=int(row["candidate_artifact_size_bytes"]),
            expected_format=row["candidate_artifact_format"],
            expected_python_version=row["candidate_python_version"],
            expected_superglm_version=row["candidate_superglm_version"],
            allowed_root=allowed_root,
        )
    except CandidateArtifactError as exc:
        return unavailable(
            rate_package_id,
            f"the deployed champion artifact could not be verified: {exc}",
        )
    if list(champion.X.columns) != list(parent_bundle.X.columns):
        return unavailable(
            rate_package_id,
            "the deployed champion uses a different prepared feature frame",
        )
    try:
        champion_contract = OffsetExportContract.model_validate(champion.offset_contract)
        parent_contract = OffsetExportContract.model_validate(parent_bundle.offset_contract)
    except ValueError:
        return unavailable(rate_package_id, "the deployed champion has an invalid offset contract")
    if champion_contract != parent_contract:
        return unavailable(
            rate_package_id, "the deployed champion uses a different offset contract"
        )
    return ChampionSnapshot(
        deployment_slot=deployment_slot,
        rate_package_id=rate_package_id,
        bundle=champion,
    )
