"""Capture publication baselines and load their verified SQL state for monitoring.

Publication may read a candidate artifact once. Recurring loading reads only SQL.
The immutable snapshot and source lineage are saved in the publication transaction.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.monitoring.contracts import (
    MonitoringError,
    MonitoringVariant,
    _canonical_json,
    _sha256_text,
)
from pricing_pipeline.publishing.metadata import (
    SuperGLMPublicationReceipt,
    canonical_receipt_bytes,
)

if TYPE_CHECKING:
    from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline
    from pricing_pipeline.publishing.publish import PreparedPublication
    from pricing_pipeline.workbench.core import Candidate


def _read_source_lineage(connection, model_run_id):
    schemas = schema_names_from_connectable(connection)
    package_statuses = (
        "'PUBLISHED', 'LOCAL_AUDIT'" if connection.dialect.name == "sqlite" else "'PUBLISHED'"
    )
    rows = (
        connection.execute(
            text(f"""
        SELECT mr.model_run_id, mr.model_id, pm.model_name, mr.rate_package_id,
            mr.model_version, mr.model_kind, mr.export_id, mr.manifest_id,
            mr.candidate_artifact_format, mr.candidate_artifact_sha256,
            mr.candidate_artifact_size_bytes, mr.candidate_python_version,
            mr.candidate_superglm_version, mr.model_source_sha256,
            mr.model_equivalence_sha256, mr.publication_receipt_sha256,
            mr.rating_workbook_sha256, mr.recipe_id, mr.recipe_status,
            mr.recipe_unavailable_reason,
            rp.package_version,
            rp.publication_receipt_sha256 AS package_publication_receipt_sha256,
            rp.publication_receipt_json, recipe.recipe_revision,
            recipe.recipe_sha256, recipe.recipe_format_version, recipe.recipe_json,
            manifest.model_frame_sha256, manifest.data_as_of_date,
            split_link.split_set_id, split_link.manifest_id AS split_manifest_id, split.row_order_sha256
        FROM {schemas.pricing}.MODEL_RUN AS mr
        JOIN {schemas.pricing}.PRICING_MODEL AS pm ON pm.model_id = mr.model_id
        JOIN {schemas.pricing}.PRICING_RATE_PACKAGE AS rp
          ON rp.rate_package_id = mr.rate_package_id AND rp.model_id = mr.model_id
         AND rp.model_version = mr.model_version AND rp.source_export_id = mr.export_id
        JOIN {schemas.pricing}.DATASET_MANIFEST AS manifest ON manifest.manifest_id = mr.manifest_id
        LEFT JOIN {schemas.pricing}.MODEL_RECIPE AS recipe
          ON recipe.recipe_id = mr.recipe_id AND recipe.model_id = mr.model_id
        LEFT JOIN {schemas.mlops}.MODEL_RUN_SPLIT_SET AS split_link
          ON split_link.model_run_id = mr.model_run_id
         AND split_link.dataset_role = 'training' AND split_link.split_role = 'validation'
        LEFT JOIN {schemas.pricing}.CV_SPLIT_SET AS split ON split.split_set_id = split_link.split_set_id
        WHERE mr.model_run_id = :run AND mr.run_status = 'SUCCESS' AND rp.package_status IN ({package_statuses})
        """),
            {"run": model_run_id},
        )
        .mappings()
        .all()
    )
    if len(rows) != 1:
        raise MonitoringError(
            "monitoring baseline must identify one successful published model run"
        )
    row = dict(rows[0])
    split_manifest_id = row.pop("split_manifest_id")
    if row["split_set_id"] is not None and split_manifest_id != row["manifest_id"]:
        raise MonitoringError("monitoring baseline split does not match its training manifest")
    training_manifests = (
        connection.execute(
            text(
                f"SELECT manifest_id FROM {schemas.mlops}.MODEL_RUN_DATASET WHERE model_run_id=:run AND dataset_role='training'"
            ),
            {"run": model_run_id},
        )
        .scalars()
        .all()
    )
    if training_manifests != [row["manifest_id"]]:
        raise MonitoringError("monitoring baseline must have one matching training dataset link")
    receipt_json = row.pop("publication_receipt_json")
    try:
        receipt = SuperGLMPublicationReceipt.model_validate_json(receipt_json)
        receipt_sha256 = _sha256_text(canonical_receipt_bytes(receipt).decode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise MonitoringError("SQL baseline publication receipt is invalid") from exc
    if (
        receipt_sha256 != row["publication_receipt_sha256"]
        or receipt_sha256 != row["package_publication_receipt_sha256"]
    ):
        raise MonitoringError("SQL baseline publication receipt hash does not match its lineage")
    recipe_json = row.pop("recipe_json")
    if row["recipe_status"] == "CAPTURED":
        try:
            recipe = json.loads(recipe_json)
            canonical_recipe = _canonical_json(recipe)
        except (TypeError, ValueError) as exc:
            raise MonitoringError("SQL baseline recipe is invalid") from exc
        if (
            not isinstance(recipe, dict)
            or canonical_recipe != recipe_json
            or _sha256_text(recipe_json) != row["recipe_sha256"]
            or recipe.get("format_version") != row["recipe_format_version"]
        ):
            raise MonitoringError("SQL baseline recipe hash or format does not match its lineage")
    row = {
        key: value.isoformat() if isinstance(value, date | datetime) else value
        for key, value in row.items()
    }
    # SQL Server uses BIGINT, while the offline audit mirror stores run IDs as text.
    if str(row["model_run_id"]).isdigit():
        row["model_run_id"] = int(row["model_run_id"])
    return row


def _stored_row(connection, model_run_id):
    schema = schema_names_from_connectable(connection).pricing
    return (
        connection.execute(
            text(f"SELECT * FROM {schema}.MODEL_MONITORING_BASELINE WHERE model_run_id=:run"),
            {"run": model_run_id},
        )
        .mappings()
        .one_or_none()
    )


def _verify_stored_row(connection, row):
    source_json = row["source_lineage_json"]
    try:
        source = json.loads(source_json)
    except (TypeError, ValueError) as exc:
        raise MonitoringError("stored monitoring baseline source lineage is invalid") from exc
    if (
        not isinstance(source, dict)
        or _canonical_json(source) != source_json
        or _sha256_text(source_json) != row["source_lineage_sha256"]
    ):
        raise MonitoringError("stored monitoring baseline source lineage hash is invalid")
    current = _read_source_lineage(connection, row["model_run_id"])
    if current["row_order_sha256"] is None and current["split_set_id"] is None:
        current["row_order_sha256"] = source.get("row_order_sha256")
    if source != current or any(
        str(row[key]) != str(source[key]) for key in ("model_run_id", "model_id", "rate_package_id")
    ):
        raise MonitoringError("stored monitoring baseline does not match SQL source lineage")
    if row["capture_status"] == "CAPTURED":
        _verify_snapshot_document(row, source)
    return source


def _verify_snapshot_document(row, source):
    snapshot_json = row["snapshot_json"]
    if _sha256_text(snapshot_json) != row["snapshot_sha256"]:
        raise MonitoringError("stored monitoring baseline snapshot hash is invalid")
    try:
        snapshot = json.loads(snapshot_json)
    except (TypeError, ValueError) as exc:
        raise MonitoringError("stored monitoring baseline snapshot JSON is invalid") from exc
    if (
        not isinstance(snapshot, dict)
        or _canonical_json(snapshot) != snapshot_json
        or snapshot.get("schema_version") != row["snapshot_schema_version"]
        or snapshot.get("superglm_version") != row["superglm_version"]
    ):
        raise MonitoringError(
            "stored monitoring baseline snapshot format does not match its SQL metadata"
        )
    bundle_identity = snapshot.get("bundle_identity")
    identity_fields = (
        "model_name",
        "model_version",
        "export_id",
        "manifest_id",
        "split_set_id",
        "row_order_sha256",
        "model_source_sha256",
        "model_frame_sha256",
    )
    if not isinstance(bundle_identity, dict) or any(
        bundle_identity.get(key) != source[key] for key in identity_fields
    ):
        raise MonitoringError(
            "stored monitoring snapshot bundle identity does not match SQL source lineage"
        )
    try:
        receipt = SuperGLMPublicationReceipt.model_validate(snapshot.get("receipt"))
        receipt_sha256 = _sha256_text(canonical_receipt_bytes(receipt).decode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise MonitoringError("stored monitoring snapshot receipt is invalid") from exc
    if receipt_sha256 != source["publication_receipt_sha256"]:
        raise MonitoringError(
            "stored monitoring snapshot receipt does not match the published package"
        )


def save_publication_monitoring_baseline(
    connection, *, model_run_id: int | str, prepared: PreparedPublication
) -> None:
    """Capture supported state, or record why it is unavailable, before commit."""
    from pricing_pipeline.modeling.monitoring.snapshot import restore_monitoring_snapshot
    from pricing_pipeline.workbench.artifacts import load_candidate_bundle

    build = prepared.build
    monitoring_baseline, monitoring_variant = None, None
    if getattr(build, "monitor_run_id", None) is not None:
        from pricing_pipeline.publishing.monitoring import validate_monitoring_publication

        observation = validate_monitoring_publication(connection, build)
        parent = _stored_row(connection, observation["baseline_model_run_id"])
        if parent is None or parent["capture_status"] != "CAPTURED":
            raise MonitoringError(
                "monitoring publication requires its baseline's captured SQL state"
            )
        _verify_stored_row(connection, parent)
        monitoring_baseline = restore_monitoring_snapshot(
            parent["snapshot_json"], expected_sha256=parent["snapshot_sha256"]
        )
        monitoring_variant = MonitoringVariant(observation["variant_code"])

    existing = _stored_row(connection, model_run_id)
    if existing is not None:
        _verify_stored_row(connection, existing)
        if monitoring_baseline is not None:
            if existing["capture_status"] != "CAPTURED":
                raise MonitoringError("monitoring challenger must have captured SQL state")
            captured = restore_monitoring_snapshot(
                existing["snapshot_json"], expected_sha256=existing["snapshot_sha256"]
            )
            if (
                captured.declared_monitoring_policy
                != monitoring_baseline.declared_monitoring_policy
            ):
                raise MonitoringError(
                    "monitoring challenger declared policy differs from its baseline"
                )
        return
    source = _read_source_lineage(connection, model_run_id)
    if source["export_id"] != build.export_id:
        # An equivalent publication belongs to its original run and artifacts.
        if monitoring_baseline is not None:
            raise MonitoringError("monitoring challenger cannot reuse an unrelated publication")
        return
    bundle = load_candidate_bundle(
        build.candidate_artifact_path,
        expected_sha256=build.candidate_artifact_sha256,
        expected_size_bytes=build.candidate_artifact_size_bytes,
        expected_format=build.candidate_artifact_format,
        expected_python_version=build.candidate_python_version,
        expected_superglm_version=build.candidate_superglm_version,
        allowed_root=prepared.allowed_artifact_root,
    )
    if bundle.recipe_capture != build.recipe_capture:
        raise MonitoringError(
            "publication monitoring baseline recipe does not match build evidence"
        )
    _save_captured_baseline(
        connection,
        source,
        bundle,
        created_by=build.created_by,
        monitoring_baseline=monitoring_baseline,
        monitoring_variant=monitoring_variant,
    )


def _save_captured_baseline(
    connection,
    source,
    bundle,
    *,
    created_by,
    monitoring_baseline=None,
    monitoring_variant=None,
):
    from pricing_pipeline.modeling.monitoring.snapshot import (
        MonitoringSnapshotUnsupported,
        capture_monitoring_snapshot,
        restore_monitoring_snapshot,
    )

    for key in (
        "model_name",
        "model_version",
        "export_id",
        "manifest_id",
        "split_set_id",
        "model_source_sha256",
        "model_frame_sha256",
    ):
        if getattr(bundle, key) != source[key]:
            raise MonitoringError(
                f"publication monitoring baseline {key} does not match SQL lineage"
            )
    if (
        bundle.recipe_capture.status != source["recipe_status"]
        or bundle.recipe_capture.sha256 != source["recipe_sha256"]
    ):
        raise MonitoringError("publication monitoring baseline recipe does not match SQL lineage")
    if (
        source["row_order_sha256"] is not None
        and source["row_order_sha256"] != bundle.row_order_sha256
    ):
        raise MonitoringError(
            "publication monitoring baseline row order does not match SQL lineage"
        )
    source["row_order_sha256"] = bundle.row_order_sha256
    source_json = _canonical_json(source)
    if monitoring_baseline is not None:
        from pricing_pipeline.modeling.monitoring.invariants import _verify_monitoring_invariants

        _verify_monitoring_invariants(
            monitoring_baseline,
            bundle.fitted_model,
            variant=monitoring_variant,
            contract=monitoring_baseline.model_fit_contract(),
            offset_contract=bundle.offset_contract,
            fit_sample_weight_name=bundle.fit_sample_weight_name,
            export_weight_name=bundle.export_weight_name,
            input_transforms=bundle.input_transforms,
        )
    try:
        snapshot = (
            capture_monitoring_snapshot(bundle)
            if monitoring_baseline is None
            else capture_monitoring_snapshot(
                bundle,
                declared_monitoring_policy=monitoring_baseline.declared_monitoring_policy,
            )
        )
    except MonitoringSnapshotUnsupported as exc:
        if monitoring_baseline is not None:
            raise MonitoringError(
                f"monitoring challenger SQL snapshot is unavailable: {exc}"
            ) from exc
        status = "UNAVAILABLE"
        reason = (str(exc).strip() or "The model cannot be captured as a monitoring snapshot.")[
            :2000
        ]
        snapshot = None
    else:
        status, reason = "CAPTURED", None
        _verify_snapshot_document(
            {
                "snapshot_json": snapshot.snapshot_json,
                "snapshot_sha256": snapshot.snapshot_sha256,
                "snapshot_schema_version": snapshot.schema_version,
                "superglm_version": snapshot.superglm_version,
            },
            source,
        )
        restored = restore_monitoring_snapshot(
            snapshot.snapshot_json, expected_sha256=snapshot.snapshot_sha256
        )
        if (
            monitoring_baseline is not None
            and restored.declared_monitoring_policy
            != monitoring_baseline.declared_monitoring_policy
        ):
            raise MonitoringError("captured challenger policy differs from its SQL baseline")
    schema = schema_names_from_connectable(connection).pricing
    connection.execute(
        text(f"""INSERT INTO {schema}.MODEL_MONITORING_BASELINE
        (model_run_id, model_id, rate_package_id, capture_status, unavailable_reason,
         snapshot_schema_version, snapshot_json, snapshot_sha256, superglm_version,
         source_lineage_json, source_lineage_sha256, created_by)
        VALUES (:run, :model, :package, :status, :reason, :version, :snapshot, :sha,
                :superglm, :source, :source_sha, :creator)"""),
        {
            "run": source["model_run_id"],
            "model": source["model_id"],
            "package": source["rate_package_id"],
            "status": status,
            "reason": reason,
            "version": None if snapshot is None else snapshot.schema_version,
            "snapshot": None if snapshot is None else snapshot.snapshot_json,
            "sha": None if snapshot is None else snapshot.snapshot_sha256,
            "superglm": None if snapshot is None else snapshot.superglm_version,
            "source": source_json,
            "source_sha": _sha256_text(source_json),
            "creator": created_by,
        },
    )


def capture_existing_monitoring_baseline(candidate: Candidate) -> str | None:
    """Capture an older published candidate once without refitting; return its hash.

    The workbench verifies the existing artifact before capture. An unsupported
    model records its reason and returns None. Existing captures remain immutable.
    """
    from pricing_pipeline.publishing.recipes import lock_model
    from pricing_pipeline.workbench.core import Candidate

    if not isinstance(candidate, Candidate):
        raise TypeError("candidate must be a verified workbench Candidate")
    workbench = candidate.workbench
    refreshed = workbench.open(candidate.model_name, package_version=candidate.package_version)
    if (
        refreshed.model_run_id != candidate.model_run_id
        or refreshed.rate_package_id != candidate.rate_package_id
    ):
        raise MonitoringError("candidate publication identity changed before baseline capture")
    with workbench.engine.begin() as connection:
        lock_model(connection, int(refreshed.technical["model_id"]))
        existing = _stored_row(connection, refreshed.model_run_id)
        if existing is not None:
            _verify_stored_row(connection, existing)
            return existing["snapshot_sha256"]
        source = _read_source_lineage(connection, refreshed.model_run_id)
        for key in (
            "candidate_artifact_sha256",
            "candidate_artifact_format",
            "candidate_artifact_size_bytes",
            "candidate_python_version",
            "candidate_superglm_version",
            "publication_receipt_sha256",
        ):
            if source[key] != refreshed.technical[key]:
                raise MonitoringError(f"candidate {key} changed before baseline capture")
        _save_captured_baseline(
            connection, source, refreshed.bundle, created_by="monitoring-baseline-migration"
        )
        return _stored_row(connection, refreshed.model_run_id)["snapshot_sha256"]


def load_monitoring_baseline(
    engine, model_name: str, *, deployment_slot: str = "PRODUCTION"
) -> SqlBaseline:
    """Load the current deployment's verified monitoring state using SQL only."""
    from pricing_pipeline.modeling.monitoring.snapshot import restore_monitoring_snapshot

    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name is required")
    if not isinstance(deployment_slot, str) or not deployment_slot.strip():
        raise ValueError("deployment_slot is required")
    schema = schema_names_from_connectable(engine).pricing
    with engine.connect() as connection:
        deployments = (
            connection.execute(
                text(f"""SELECT deployment.deployment_id, deployment.deployment_slot, mr.model_run_id
            FROM {schema}.PRICING_MODEL_DEPLOYMENT AS deployment
            JOIN {schema}.PRICING_MODEL AS model ON model.model_id=deployment.model_id
            JOIN {schema}.PRICING_RATE_PACKAGE AS package
              ON package.rate_package_id=deployment.rate_package_id AND package.model_id=model.model_id
            JOIN {schema}.MODEL_RUN AS mr
              ON mr.rate_package_id=package.rate_package_id AND mr.model_id=model.model_id
            WHERE model.model_name=:name AND deployment.deployment_slot=:slot
              AND deployment.effective_to_ts IS NULL
              AND mr.run_status='SUCCESS' AND package.package_status='PUBLISHED'"""),
                {"name": model_name.strip(), "slot": deployment_slot.strip().upper()},
            )
            .mappings()
            .all()
        )
        if len(deployments) != 1:
            raise MonitoringError(
                "monitoring requires one current deployed package with one successful model run"
            )
        deployment = deployments[0]
        row = _stored_row(connection, deployment["model_run_id"])
        if row is None:
            raise MonitoringError(
                "The deployed model has no SQL monitoring baseline. Capture its verified publication artifacts once before recurring monitoring."
            )
        identity = _verify_stored_row(connection, row)
        if row["capture_status"] != "CAPTURED":
            raise MonitoringError(
                f"SQL monitoring baseline is unavailable: {row['unavailable_reason']}"
            )
        restored = restore_monitoring_snapshot(
            row["snapshot_json"], expected_sha256=row["snapshot_sha256"]
        )
        identity.update(
            deployment_id=int(deployment["deployment_id"]),
            deployment_slot=deployment["deployment_slot"],
            snapshot_sha256=row["snapshot_sha256"],
        )
        return replace(restored, identity=identity)


def verify_monitoring_snapshot_identity(connection, *, model_run_id, snapshot_sha256):
    """Recheck the snapshot and SQL lineage in the monitoring write transaction."""
    row = _stored_row(connection, model_run_id)
    if (
        row is None
        or row["capture_status"] != "CAPTURED"
        or row["snapshot_sha256"] != snapshot_sha256
    ):
        raise MonitoringError("verified monitoring snapshot does not match the stored SQL baseline")
    _verify_stored_row(connection, row)
