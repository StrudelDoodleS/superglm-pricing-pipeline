"""Verify exact retries and equivalent editor publications against stored lineage.

Check package, model-run, recipe, submission and manual-policy evidence before
allowing the workflow to reuse a saved publication."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.publishing.editor_contracts import (
    EditorPublicationResult,
    _editor_export_id,
    _manual_policy_provenance_identity,
    _submission_model_kind,
)
from pricing_pipeline.publishing.editor_parent import _verify_model_frame_sha256
from pricing_pipeline.publishing.identity import canonical_json
from pricing_pipeline.publishing.publish import (
    CompletedModelPublishResult,
)
from pricing_pipeline.publishing.recipes import validate_recipe_capture
from pricing_pipeline.workbench.artifacts import (
    CandidateArtifactError,
    load_candidate_bundle,
)
from pricing_pipeline.workbench.submission import (
    EditorSubmission,
    EditorSubmissionError,
    sha256_file,
)


def _verify_reused_publication(
    *,
    engine,
    submission: EditorSubmission,
    publication: CompletedModelPublishResult,
    allowed_root: str | Path,
) -> int | None:
    if publication.deduplicated:
        if publication.model_run_id is None:
            raise EditorSubmissionError(
                "equivalent editor package has no durable model-run lineage"
            )
        row = _load_reused_publication_lineage(
            engine,
            rate_package_id=publication.rate_package_id,
            model_run_id=publication.model_run_id,
        )
        if _submission_model_kind(submission) == "MANUAL_EDIT":
            _require_matching_manual_policy_lineage(
                submission=submission,
                row=row,
            )
        return _require_reused_publication_lineage(publication=publication, row=row)
    if not publication.was_existing:
        return None
    existing = _resolve_existing_editor_publication(
        engine,
        submission,
        allowed_root=allowed_root,
    )
    if existing is None or existing.rate_package_id != publication.rate_package_id:
        raise EditorSubmissionError("existing editor package changed before lineage validation")
    return existing.parent_rate_package_id


def _load_reused_publication_lineage(
    engine,
    *,
    rate_package_id: int,
    model_run_id: int,
) -> Mapping[str, Any] | None:
    schemas = schema_names_from_connectable(engine)
    with engine.connect() as connection:
        return (
            connection.execute(
                text(
                    f"""
                    SELECT
                        pm.model_name,
                        rp.parent_rate_package_id,
                        rp.package_status,
                        rp.revision_metadata_json,
                        mr.model_run_id,
                        mr.parent_model_run_id,
                        mr.run_status,
                        mr.manifest_id,
                        mr.model_kind,
                        mr.model_equivalence_sha256
                    FROM {schemas.pricing}.PRICING_RATE_PACKAGE AS rp
                    JOIN {schemas.pricing}.PRICING_MODEL AS pm
                      ON pm.model_id = rp.model_id
                    JOIN {schemas.pricing}.MODEL_RUN AS mr
                      ON mr.rate_package_id = rp.rate_package_id
                    WHERE rp.rate_package_id = :rate_package_id
                      AND mr.model_run_id = :model_run_id
                    """
                ),
                {
                    "rate_package_id": rate_package_id,
                    "model_run_id": model_run_id,
                },
            )
            .mappings()
            .one_or_none()
        )


def _require_reused_publication_lineage(
    *,
    publication: CompletedModelPublishResult,
    row: Mapping[str, Any] | None,
) -> int:
    if row is None or row.get("parent_rate_package_id") is None:
        raise EditorSubmissionError("equivalent editor package has unusable durable lineage")
    expected = {
        "model_name": publication.model_name,
        "package_status": "PUBLISHED",
        "model_run_id": publication.model_run_id,
        "run_status": "SUCCESS",
        "manifest_id": publication.manifest_id,
        "model_kind": publication.model_kind,
        "model_equivalence_sha256": publication.model_equivalence_sha256,
    }
    mismatches = [
        field_name
        for field_name, expected_value in expected.items()
        if str(row.get(field_name)) != str(expected_value)
    ]
    if mismatches:
        raise EditorSubmissionError(
            "equivalent editor package has incompatible lineage: " + ", ".join(mismatches)
        )
    return int(row["parent_rate_package_id"])


def _require_matching_manual_policy_lineage(
    *,
    submission: EditorSubmission,
    row: Mapping[str, Any] | None,
) -> None:
    mismatches: list[str] = []
    stored_revision: Mapping[str, Any] | None = None
    if row is None:
        mismatches.append("package/run provenance is missing")
    else:
        if row.get("parent_rate_package_id") != submission.parent_rate_package_id:
            mismatches.append("parent_rate_package_id")
        if row.get("parent_model_run_id") != submission.parent_model_run_id:
            mismatches.append("parent_model_run_id")
        raw_revision = row.get("revision_metadata_json")
        try:
            decoded_revision = (
                json.loads(raw_revision) if isinstance(raw_revision, str) else raw_revision
            )
        except json.JSONDecodeError:
            decoded_revision = None
        if isinstance(decoded_revision, Mapping):
            stored_revision = decoded_revision
        else:
            mismatches.append("revision_metadata_json")

    if stored_revision is not None:
        if stored_revision.get("kind") != "SUPERGLM_MANUAL_EDIT":
            mismatches.append("revision kind")
        if stored_revision.get("parent_rate_package_id") != submission.parent_rate_package_id:
            mismatches.append("revision parent_rate_package_id")
        if stored_revision.get("parent_model_run_id") != submission.parent_model_run_id:
            mismatches.append("revision parent_model_run_id")

        requested_policy_identity = _manual_policy_provenance_identity(
            getattr(submission, "edit_metadata", None)
        )
        stored_policy_identity = _manual_policy_provenance_identity(
            stored_revision.get("edit_metadata")
        )
        if requested_policy_identity is None or stored_policy_identity != requested_policy_identity:
            mismatches.append("manual adjustment policy metadata")

    if mismatches:
        raise EditorSubmissionError(
            "equivalent MANUAL_EDIT package has incompatible immutable policy lineage "
            f"({', '.join(mismatches)}); the one-package-per-equivalent-model identity "
            "cannot preserve the requested replay contract"
        )


def _require_existing_submission_revision(
    row: Mapping[str, Any],
    submission: EditorSubmission,
) -> None:
    raw_revision = row.get("revision_metadata_json")
    try:
        revision = json.loads(raw_revision) if isinstance(raw_revision, str) else raw_revision
    except json.JSONDecodeError:
        revision = None
    if not isinstance(revision, Mapping):
        raise EditorSubmissionError(
            "existing editor publication signed submission metadata does not match: "
            "revision_metadata_json"
        )

    expected_kind = (
        "SUPERGLM_MANUAL_EDIT"
        if _submission_model_kind(submission) == "MANUAL_EDIT"
        else "SUPERGLM_EDITOR"
    )
    expected = {
        "kind": expected_kind,
        "submission_id": submission.submission_id,
        "submission_path": submission.path,
        "submission_sha256": submission.sha256,
        "parent_rate_package_id": submission.parent_rate_package_id,
        "parent_model_run_id": submission.parent_model_run_id,
    }
    mismatches = [
        field_name
        for field_name, expected_value in expected.items()
        if revision.get(field_name) != expected_value
    ]
    requested_edit_metadata = getattr(submission, "edit_metadata", None)
    stored_edit_metadata = revision.get("edit_metadata")
    try:
        requested_edit_identity = (
            None
            if requested_edit_metadata is None
            else canonical_json(dict(requested_edit_metadata))
        )
        stored_edit_identity = (
            None if stored_edit_metadata is None else canonical_json(dict(stored_edit_metadata))
        )
    except (TypeError, ValueError):  # fmt: skip
        requested_edit_identity = None
        stored_edit_identity = "invalid"
    if stored_edit_identity != requested_edit_identity:
        mismatches.append("edit_metadata")
    if _submission_model_kind(submission) == "MANUAL_EDIT":
        requested_policy_identity = _manual_policy_provenance_identity(requested_edit_metadata)
        stored_policy_identity = _manual_policy_provenance_identity(stored_edit_metadata)
        if requested_policy_identity is None or stored_policy_identity != requested_policy_identity:
            mismatches.append("manual adjustment policy lineage")
    if mismatches:
        raise EditorSubmissionError(
            "existing editor publication signed submission metadata does not match: "
            + ", ".join(mismatches)
        )


def _resolve_existing_editor_publication(
    engine,
    submission: EditorSubmission,
    *,
    allowed_root: str | Path,
) -> EditorPublicationResult | None:
    schemas = schema_names_from_connectable(engine)
    query = text(
        f"""
        SELECT
            pm.model_name,
            rp.rate_package_id,
            rp.package_version,
            rp.package_status,
            rp.parent_rate_package_id,
            rp.revision_metadata_json,
            mr.model_run_id,
            mr.parent_model_run_id,
            mr.run_status,
            mr.model_version,
            mr.model_kind,
            mr.export_id,
            mr.manifest_id,
            manifest.model_frame_sha256,
            mr.rating_workbook_path,
            mr.rating_workbook_sha256,
            split_link.split_set_id,
            mr.model_source_sha256,
            mr.recipe_status, recipe.recipe_sha256, recipe.recipe_json, recipe.recipe_format_version,
            mr.candidate_artifact_path,
            mr.candidate_artifact_sha256,
            mr.candidate_artifact_format,
            mr.candidate_artifact_size_bytes,
            mr.candidate_python_version,
            mr.candidate_superglm_version
        FROM {schemas.pricing}.PRICING_RATE_PACKAGE AS rp
        JOIN {schemas.pricing}.PRICING_MODEL AS pm
          ON pm.model_id = rp.model_id
        LEFT JOIN {schemas.pricing}.MODEL_RUN AS mr
          ON mr.rate_package_id = rp.rate_package_id
        LEFT JOIN {schemas.pricing}.MODEL_RECIPE AS recipe ON recipe.model_id=mr.model_id AND recipe.recipe_id=mr.recipe_id
        LEFT JOIN {schemas.pricing}.DATASET_MANIFEST AS manifest
          ON manifest.manifest_id = mr.manifest_id
        LEFT JOIN {schemas.mlops}.MODEL_RUN_SPLIT_SET AS split_link
          ON split_link.model_run_id = mr.model_run_id
         AND split_link.manifest_id = mr.manifest_id
         AND split_link.dataset_role = 'training'
         AND split_link.split_role = 'validation'
        WHERE pm.model_name = :model_name
          AND rp.parent_rate_package_id = :parent_rate_package_id
          AND rp.source_export_id = :export_id
        """
    )
    with engine.begin() as connection:
        rows = list(
            connection.execute(
                query,
                {
                    "model_name": submission.model_name,
                    "parent_rate_package_id": submission.parent_rate_package_id,
                    "export_id": _editor_export_id(submission),
                },
            )
            .mappings()
            .all()
        )
    if not rows:
        return None
    if len(rows) != 1:
        raise EditorSubmissionError(
            "editor publication requires lineage repair: "
            f"expected one package/run, found {len(rows)}"
        )
    row = dict(rows[0])
    if (
        row.get("model_run_id") is None
        or str(row.get("package_status") or "").upper() != "PUBLISHED"
        or str(row.get("run_status") or "").upper() != "SUCCESS"
    ):
        raise EditorSubmissionError(
            "editor publication requires lineage repair: package/run is incomplete"
        )
    workbook_path = Path(str(row.get("rating_workbook_path") or "")).expanduser().resolve()
    root = Path(allowed_root).expanduser().resolve()
    if not workbook_path.is_relative_to(root) or not workbook_path.is_file():
        raise EditorSubmissionError(
            "existing editor publication rating workbook is missing or outside the artifact root"
        )
    expected_workbook_sha256 = str(row.get("rating_workbook_sha256") or "")
    if sha256_file(workbook_path) != expected_workbook_sha256:
        raise EditorSubmissionError(
            "existing editor publication rating workbook SHA-256 verification failed"
        )
    artifact_fields = (
        "candidate_artifact_path",
        "candidate_artifact_sha256",
        "candidate_artifact_format",
        "candidate_artifact_size_bytes",
        "candidate_python_version",
        "candidate_superglm_version",
    )
    if any(row.get(field) is None for field in artifact_fields):
        raise EditorSubmissionError(
            "editor publication requires lineage repair: candidate artifact metadata is incomplete"
        )
    expected_lineage = {
        "model_name": submission.model_name,
        "export_id": _editor_export_id(submission),
        "manifest_id": submission.manifest_id,
        "split_set_id": submission.split_set_id,
        "model_source_sha256": submission.model_source_sha256,
    }
    expected_sql_lineage = {
        **expected_lineage,
        "parent_model_run_id": submission.parent_model_run_id,
        "model_kind": _submission_model_kind(submission),
    }
    if row.get("model_kind") is None:
        row["model_kind"] = "EDITOR_EDIT"
    sql_mismatches = [
        field for field, expected in expected_sql_lineage.items() if row.get(field) != expected
    ]
    if sql_mismatches:
        raise EditorSubmissionError(
            "existing editor publication SQL lineage does not match the submission: "
            + ", ".join(sql_mismatches)
        )
    _require_existing_submission_revision(row, submission)
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
        raise EditorSubmissionError(
            f"existing editor publication candidate artifact failed verification: {exc}"
        ) from exc
    validate_recipe_capture(row, bundle.recipe_capture)
    expected_bundle = {
        **expected_lineage,
        "model_version": row.get("model_version"),
    }
    bundle_mismatches = [
        field for field, expected in expected_bundle.items() if getattr(bundle, field) != expected
    ]
    if bundle_mismatches:
        raise EditorSubmissionError(
            "existing editor publication bundle lineage does not match the submission: "
            + ", ".join(bundle_mismatches)
        )
    _verify_model_frame_sha256(
        bundle,
        row.get("model_frame_sha256"),
        context="existing editor publication",
    )
    return EditorPublicationResult(
        submission_id=submission.submission_id,
        model_name=str(row["model_name"]),
        parent_rate_package_id=int(row["parent_rate_package_id"]),
        rate_package_id=int(row["rate_package_id"]),
        package_version=int(row["package_version"]),
        model_run_id=int(row["model_run_id"]),
        package_status=str(row["package_status"]),
        was_existing=True,
        model_kind=_submission_model_kind(submission),
    )
