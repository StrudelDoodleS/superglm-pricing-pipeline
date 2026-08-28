from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.model_registry import ModelRegistryError, get_pricing_model
from pricing_pipeline.publishing.rating_tables import (
    RatingTables,
    StagingExport,
    build_staging_frames,
    model_equivalence_sha256,
    prepare_rating_tables,
    rating_workbook_model_equivalence_sha256,
    staging_content_sha256,
)
from pricing_pipeline.publishing.staging_lock import acquire_staging_export_lock

__all__ = [
    "StagingExport",
    "build_staging_frames",
    "insert_staging_frames",
    "model_equivalence_sha256",
    "rating_workbook_model_equivalence_sha256",
    "stage_rating_export",
    "staging_content_sha256",
]


def _resolve_registered_model_id(con, args: StagingExport) -> int:
    model_id = args.model_id
    if model_id is not None:
        return int(model_id)

    record = get_pricing_model(con, args.model_name)
    if record is None:
        raise ModelRegistryError(
            f"model_name {args.model_name!r} is not registered; "
            "run explicit model registration first"
        )

    mismatches: list[str] = []
    if record.target_name != args.target_name:
        mismatches.append(f"target_name db={record.target_name!r} staging={args.target_name!r}")
    if record.model_type != args.model_type:
        mismatches.append(f"model_type db={record.model_type!r} staging={args.model_type!r}")
    if record.model_status != "ACTIVE":
        mismatches.append(f"model_status db={record.model_status!r} expected='ACTIVE'")

    if mismatches:
        raise ModelRegistryError(
            f"registered model {args.model_name!r} does not match staged export: "
            + "; ".join(mismatches)
        )
    return record.model_id


def insert_staging_frames(
    engine,
    args: StagingExport,
    tables: RatingTables,
) -> None:
    for field_name, digest in (
        ("staging_content_sha256", tables.staging_content_sha256),
        ("model_equivalence_sha256", tables.model_equivalence_sha256),
    ):
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    schemas = schema_names_from_connectable(engine)
    with engine.begin() as con:
        acquire_staging_export_lock(con, args.export_id)
        model_id = _resolve_registered_model_id(con, args)

        if args.replace:
            con.execute(
                text("DELETE FROM pricing_stg.STG_TERM_METADATA WHERE export_id = :export_id"),
                {"export_id": args.export_id},
            )
            con.execute(
                text("DELETE FROM pricing_stg.STG_CELL_LEVEL WHERE export_id = :export_id"),
                {"export_id": args.export_id},
            )
            con.execute(
                text("DELETE FROM pricing_stg.STG_RATE_CELL WHERE export_id = :export_id"),
                {"export_id": args.export_id},
            )
            con.execute(
                text("DELETE FROM pricing_stg.STG_RATING_EXPORT WHERE export_id = :export_id"),
                {"export_id": args.export_id},
            )

        tables.export_frame.to_sql(
            "STG_RATING_EXPORT",
            con,
            schema=schemas.pricing_staging,
            if_exists="append",
            index=False,
        )
        con.execute(
            text(
                "UPDATE pricing_stg.STG_RATING_EXPORT "
                "SET model_id = :model_id, "
                "staging_content_sha256 = :staging_content_sha256, "
                "model_equivalence_sha256 = :model_equivalence_sha256 "
                "WHERE export_id = :export_id"
            ),
            {
                "export_id": args.export_id,
                "model_id": model_id,
                "staging_content_sha256": tables.staging_content_sha256,
                "model_equivalence_sha256": tables.model_equivalence_sha256,
            },
        )
        tables.rate_cells.to_sql(
            "STG_RATE_CELL",
            con,
            schema=schemas.pricing_staging,
            if_exists="append",
            index=False,
            chunksize=5000,
        )
        tables.cell_levels.to_sql(
            "STG_CELL_LEVEL",
            con,
            schema=schemas.pricing_staging,
            if_exists="append",
            index=False,
            chunksize=5000,
        )
        if not tables.term_metadata.empty:
            tables.term_metadata.to_sql(
                "STG_TERM_METADATA",
                con,
                schema=schemas.pricing_staging,
                if_exists="append",
                index=False,
                chunksize=5000,
            )


def stage_rating_export(
    engine,
    *,
    workbook_path: Path,
    export_id: str,
    model_name: str,
    model_version: str | None,
    effective_from: str | None,
    target_name: str = "ClaimNb",
    model_type: str = "superglm_poisson",
    effective_to: str | None = None,
    created_by: str = "python",
    replace: bool = False,
    model_id: int | None = None,
    publication_receipt_path: str | Path,
    publication_receipt_sha256: str,
) -> str:
    build = ApprovedModelBuild.model_construct(
        model_id=model_id,
        model_name=model_name,
        model_version=model_version,
        target_name=target_name,
        model_type=model_type,
        export_id=export_id,
        effective_from=effective_from,
        created_by=created_by,
        publication_receipt_path=str(publication_receipt_path),
        publication_receipt_sha256=publication_receipt_sha256,
    )
    model_config = ModelBuildConfig(
        model_name=model_name,
        model_label=model_name,
        target_name=target_name,
        model_type=model_type,
        deployment_slot=model_name,
    )
    tables = prepare_rating_tables(
        workbook_path=Path(workbook_path),
        build=build,
        model_config=model_config,
        effective_to=effective_to,
    )
    args = StagingExport(
        workbook_path=Path(workbook_path),
        export_id=export_id,
        model_name=model_name,
        target_name=target_name,
        model_type=model_type,
        model_version=model_version,
        effective_from=effective_from,
        effective_to=effective_to,
        interaction_features={},
        created_by=created_by,
        replace=replace,
        model_id=model_id,
    )
    insert_staging_frames(engine, args, tables)
    return tables.staging_content_sha256
