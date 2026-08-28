"""Python-side model equivalence checks performed before SQL staging."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.models.spec import ApprovedModelBuild


class ModelEquivalenceError(RuntimeError):
    """Raised when equivalence evidence or prior durable lineage is inconsistent."""


def clean_identifier(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value).strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def canonical_json(value: object) -> str:
    """Serialize identity-bearing JSON with one stable representation."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def identity_value(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def immutable_conflicts(
    *,
    stored: Mapping[str, object],
    requested: Mapping[str, object],
    fields: Sequence[str],
) -> tuple[str, ...]:
    return tuple(
        field
        for field in fields
        if identity_value(stored.get(field)) != identity_value(requested.get(field))
    )


def bind_model_equivalence(
    build: ApprovedModelBuild,
    *,
    calculated_sha256: str,
) -> ApprovedModelBuild:
    existing = build.model_equivalence_sha256
    if existing is not None and existing != calculated_sha256:
        raise ModelEquivalenceError(
            "completed build equivalence fingerprint does not match prepared rating tables"
        )
    return build.model_copy(update={"model_equivalence_sha256": calculated_sha256})


@dataclass(frozen=True)
class EquivalentModelPublication:
    model_id: int
    model_name: str
    model_version: str
    export_id: str
    rate_package_id: int
    package_version: int
    package_status: str
    parent_rate_package_id: int | None
    model_run_id: int
    manifest_id: str
    split_set_id: str | None
    model_kind: str
    model_equivalence_sha256: str
    rating_workbook_path: str
    mlflow_run_id: str | None
    publication_receipt_path: str | None
    publication_receipt_sha256: str | None


def date_identity(value: object) -> str | None:
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


def find_equivalent_publication(
    engine,
    *,
    build: ApprovedModelBuild,
) -> EquivalentModelPublication | None:
    """Read SQL lineage for the same model, dataset version, kind, and rating fingerprint."""
    digest = build.model_equivalence_sha256
    if digest is None:
        raise ModelEquivalenceError(
            "calculate model equivalence before checking prior publications"
        )
    schemas = schema_names_from_connectable(engine)
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    f"""
                    SELECT
                        rp.model_id,
                        pm.model_name,
                        rp.model_version,
                        rp.source_export_id,
                        rp.rate_package_id,
                        rp.package_version,
                        rp.package_status,
                        rp.parent_rate_package_id,
                        mr.model_run_id,
                        mr.manifest_id,
                        split_link.manifest_id AS split_manifest_id,
                        split_link.split_set_id,
                        mr.model_kind,
                        mr.model_equivalence_sha256,
                        mr.rating_workbook_path,
                        mr.mlflow_run_id,
                        mr.publication_receipt_path,
                        mr.publication_receipt_sha256,
                        rp.effective_from_date,
                        rp.effective_to_date
                    FROM {schemas.pricing}.MODEL_RUN AS mr
                    JOIN {schemas.pricing}.PRICING_RATE_PACKAGE AS rp
                      ON rp.rate_package_id = mr.rate_package_id
                    JOIN {schemas.pricing}.PRICING_MODEL AS pm
                      ON pm.model_id = mr.model_id
                    LEFT JOIN {schemas.mlops}.MODEL_RUN_SPLIT_SET AS split_link
                      ON split_link.model_run_id = mr.model_run_id
                     AND split_link.dataset_role = 'training'
                     AND split_link.split_role = 'validation'
                    WHERE mr.model_id = :model_id
                      AND mr.manifest_id = :manifest_id
                      AND mr.model_kind = :model_kind
                      AND mr.model_equivalence_sha256 =
                          :model_equivalence_sha256
                      AND mr.run_status = 'SUCCESS'
                    """
                ),
                {
                    "model_id": build.model_id,
                    "manifest_id": build.manifest_id,
                    "model_kind": build.model_kind,
                    "model_equivalence_sha256": digest,
                },
            )
            .mappings()
            .all()
        )
        if len(rows) > 1:
            model_run_ids = {str(row["model_run_id"]) for row in rows}
            if len(model_run_ids) == 1:
                raise ModelEquivalenceError(
                    "equivalent model run resolves multiple training/validation split links"
                )
            raise ModelEquivalenceError(
                "equivalent rating fingerprint resolves multiple successful model runs"
            )
        if not rows:
            return None
        row = rows[0]
        training_links = connection.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {schemas.mlops}.MODEL_RUN_DATASET
                WHERE model_run_id = :model_run_id
                  AND manifest_id = :manifest_id
                  AND dataset_role = 'training'
                """
            ),
            {
                "model_run_id": row["model_run_id"],
                "manifest_id": build.manifest_id,
            },
        ).scalar_one()
    if int(training_links) != 1:
        raise ModelEquivalenceError(
            "equivalent model run does not have exactly one matching training-manifest link"
        )
    if str(row["model_name"]) != build.model_name:
        raise ModelEquivalenceError("equivalent model run has a different model name")
    split_manifest_id = row["split_manifest_id"]
    if split_manifest_id is not None and str(split_manifest_id) != build.manifest_id:
        raise ModelEquivalenceError(
            "equivalent model run split lineage points at a different manifest"
        )
    stored_effective_from = date_identity(row["effective_from_date"])
    requested_effective_from = date_identity(build.effective_from)
    if stored_effective_from != requested_effective_from:
        raise ModelEquivalenceError(
            "an equivalent model build already exists under a different "
            "effective_from date; the current schema cannot preserve a new release "
            "intent without separating model builds from rate packages "
            f"(existing={stored_effective_from!r}, requested={requested_effective_from!r})"
        )
    return EquivalentModelPublication(
        model_id=int(row["model_id"]),
        model_name=str(row["model_name"]),
        model_version=str(row["model_version"]),
        export_id=str(row["source_export_id"]),
        rate_package_id=int(row["rate_package_id"]),
        package_version=int(row["package_version"]),
        package_status=str(row["package_status"]),
        parent_rate_package_id=(
            None if row["parent_rate_package_id"] is None else int(row["parent_rate_package_id"])
        ),
        model_run_id=int(row["model_run_id"]),
        manifest_id=str(row["manifest_id"]),
        split_set_id=(None if row["split_set_id"] is None else str(row["split_set_id"])),
        model_kind=str(row["model_kind"]),
        model_equivalence_sha256=str(row["model_equivalence_sha256"]),
        rating_workbook_path=str(row["rating_workbook_path"]),
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
    )


def release_unused_model_version_reservation(
    engine,
    *,
    model_id: int,
    export_id: str,
) -> None:
    """Remove the provisional version of a build rejected as equivalent."""
    schemas = schema_names_from_connectable(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                DELETE FROM {schemas.pricing}.PRICING_MODEL_VERSION_RESERVATION
                WHERE model_id = :model_id
                  AND export_id = :export_id
                  AND NOT EXISTS (
                      SELECT 1
                      FROM {schemas.pricing}.PRICING_RATE_PACKAGE
                      WHERE model_id = :model_id
                        AND source_export_id = :export_id
                  )
                """
            ),
            {"model_id": model_id, "export_id": export_id},
        )


def canonical_revision_metadata(value: Mapping[str, object] | None) -> str | None:
    """Return the one canonical JSON identity accepted by both backends."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("revision_metadata must be a mapping")  # noqa: TRY004

    def normalise(item: object) -> object:
        if isinstance(item, Mapping):
            if not all(isinstance(key, str) for key in item):
                raise ValueError("revision_metadata keys must be strings")
            return {key: normalise(nested) for key, nested in item.items()}
        if isinstance(item, list | tuple):
            return [normalise(nested) for nested in item]
        return item

    normalised = normalise(value)
    try:
        return json.dumps(
            normalised,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except ValueError as exc:
        raise ValueError("revision_metadata must contain only finite numbers") from exc
    except TypeError as exc:
        raise ValueError("revision_metadata must contain only JSON-serializable values") from exc


__all__ = [
    "EquivalentModelPublication",
    "ModelEquivalenceError",
    "bind_model_equivalence",
    "canonical_json",
    "canonical_revision_metadata",
    "clean_identifier",
    "date_identity",
    "find_equivalent_publication",
    "identity_value",
    "immutable_conflicts",
    "release_unused_model_version_reservation",
]
