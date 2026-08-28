"""Compatibility imports for canonical publication identity operations."""

from pathlib import Path

from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.identity import (
    EquivalentModelPublication,
    ModelEquivalenceError,
    bind_model_equivalence,
    find_equivalent_publication,
    immutable_conflicts,
    release_unused_model_version_reservation,
)
from pricing_pipeline.publishing.staging import rating_workbook_model_equivalence_sha256


def ensure_model_equivalence(
    build: ApprovedModelBuild,
    *,
    effective_to: str | None = None,
) -> ApprovedModelBuild:
    """Compatibility adapter for callers not yet using prepared rating tables."""
    digest = rating_workbook_model_equivalence_sha256(
        workbook_path=Path(build.rating_workbook_path),
        export_id=build.export_id,
        model_name=build.model_name,
        model_version=build.model_version,
        target_name=build.target_name,
        model_type=build.model_type,
        effective_from=build.effective_from,
        effective_to=effective_to,
        created_by=build.created_by,
        model_id=build.model_id,
        publication_receipt_path=build.publication_receipt_path,
        publication_receipt_sha256=build.publication_receipt_sha256,
    )
    if build.model_equivalence_sha256 is not None:
        if build.model_equivalence_sha256 != digest:
            raise ModelEquivalenceError(
                "completed build model equivalence digest does not match its local workbook"
            )
        return build
    return build.model_copy(update={"model_equivalence_sha256": digest})


__all__ = [
    "EquivalentModelPublication",
    "ModelEquivalenceError",
    "bind_model_equivalence",
    "ensure_model_equivalence",
    "find_equivalent_publication",
    "immutable_conflicts",
    "release_unused_model_version_reservation",
]
