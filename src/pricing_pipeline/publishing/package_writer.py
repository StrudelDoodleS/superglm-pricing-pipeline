"""Temporary adapter for callers not yet using prepared SQL Server publication."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from sqlalchemy.engine import Connection

from pricing_pipeline.publishing.lifecycle import PublishResult
from pricing_pipeline.publishing.sqlserver import (
    _canonical_revision_metadata,
    _delete_staging_children,
    _insert_rating_tables,
    _insert_staged_draft,
    _lock_export,
    _mark_published,
)


def publish_rating_package(
    engine,
    *,
    export_id: str,
    created_by: str = "python",
    parent_rate_package_id: int | None = None,
    revision_metadata: Mapping[str, object] | None = None,
    draft_validator=None,
    package_lineage_writer: Callable[[Connection, int], int | None] | None = None,
    expected_staged_metadata: Mapping[str, object] | None = None,
    equivalence_key: Mapping[str, object] | None = None,
) -> PublishResult:
    """Forward staged legacy calls through the concrete SQL Server stages."""
    revision_metadata_json = _canonical_revision_metadata(revision_metadata)
    if draft_validator is not None and not callable(draft_validator):
        raise TypeError("draft_validator must be callable")
    if package_lineage_writer is not None and not callable(package_lineage_writer):
        raise TypeError("package_lineage_writer must be callable")
    if equivalence_key is not None:
        required_equivalence_fields = {
            "manifest_id",
            "model_kind",
            "model_equivalence_sha256",
        }
        if set(equivalence_key) != required_equivalence_fields:
            raise ValueError(
                "equivalence_key must contain exactly: "
                + ", ".join(sorted(required_equivalence_fields))
            )

    model_run_id: int | None = None
    with engine.begin() as connection:
        _lock_export(connection, export_id)
        package = _insert_staged_draft(
            connection,
            export_id=export_id,
            created_by=created_by,
            parent_rate_package_id=parent_rate_package_id,
            revision_metadata_json=revision_metadata_json,
            expected_staged_metadata=expected_staged_metadata,
            equivalence_key=equivalence_key,
        )
        if isinstance(package, PublishResult):
            return package
        _insert_rating_tables(connection, package, None)
        if draft_validator is not None:
            draft_validator(connection, package.rate_package_id)
        if package_lineage_writer is not None:
            model_run_id = package_lineage_writer(
                connection,
                package.rate_package_id,
            )
        _mark_published(connection, package.rate_package_id)
        _delete_staging_children(connection, export_id=export_id)

    return PublishResult(
        mlflow_run_id="",
        export_id=export_id,
        rate_package_id=package.rate_package_id,
        package_version=package.package_version,
        rating_workbook_path="",
        package_status="PUBLISHED",
        was_existing=False,
        model_run_id=model_run_id,
    )


__all__ = ["publish_rating_package"]
