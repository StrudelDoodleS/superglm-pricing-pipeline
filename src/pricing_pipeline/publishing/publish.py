from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.identity import bind_model_equivalence
from pricing_pipeline.publishing.lifecycle import CompletedModelPublishResult
from pricing_pipeline.publishing.metadata import SuperGLMPublicationReceipt
from pricing_pipeline.publishing.rating_tables import prepare_rating_tables
from pricing_pipeline.workbench.artifacts import CandidateBundle
from pricing_pipeline.workbench.submission import sha256_file


@dataclass(frozen=True)
class DraftVerification:
    model: Any
    bundle: CandidateBundle
    receipt: SuperGLMPublicationReceipt


@dataclass(frozen=True)
class PublicationRequest:
    build: ApprovedModelBuild
    model_config: ModelBuildConfig
    execution_name: str
    execution_id: str
    allowed_artifact_root: Path | None
    effective_to: str | None = None
    parent_rate_package_id: int | None = None
    parent_model_run_id: int | None = None
    revision_metadata: Mapping[str, object] | None = None
    verification: DraftVerification | None = None


@dataclass(frozen=True)
class PreparedPublication:
    build: ApprovedModelBuild
    model_config: ModelBuildConfig
    execution_name: str
    execution_id: str
    allowed_artifact_root: Path | None
    effective_to: str | None
    parent_rate_package_id: int | None
    parent_model_run_id: int | None
    revision_metadata: Mapping[str, object] | None
    verification: DraftVerification | None


def _required_text(value: Any, name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{name} is required")
    return str(value).strip()


def prepare_publication(request: PublicationRequest) -> PreparedPublication:
    if not isinstance(request.build, ApprovedModelBuild):
        raise TypeError("build must be an ApprovedModelBuild")
    execution_name = _required_text(request.execution_name, "execution_name")
    execution_id = _required_text(request.execution_id, "execution_id")
    return PreparedPublication(
        build=request.build,
        model_config=request.model_config,
        execution_name=execution_name,
        execution_id=execution_id,
        allowed_artifact_root=request.allowed_artifact_root,
        effective_to=request.effective_to,
        parent_rate_package_id=request.parent_rate_package_id,
        parent_model_run_id=request.parent_model_run_id,
        revision_metadata=request.revision_metadata,
        verification=request.verification,
    )


def publish_candidate(
    engine,
    request: PublicationRequest,
) -> CompletedModelPublishResult:
    """Prepare one request once and dispatch to its concrete database writer."""
    prepared = prepare_publication(request)
    workbook_path = Path(prepared.build.rating_workbook_path)
    if not workbook_path.is_file():
        raise ValueError(f"rating workbook does not exist: {workbook_path.as_posix()}")
    initial_workbook_sha256 = sha256_file(workbook_path)
    if initial_workbook_sha256 != prepared.build.rating_workbook_sha256:
        raise ValueError(
            "rating workbook SHA-256 does not match the publication request: "
            f"expected={prepared.build.rating_workbook_sha256!r}, "
            f"actual={initial_workbook_sha256!r}"
        )
    tables = prepare_rating_tables(
        workbook_path=workbook_path,
        build=prepared.build,
        model_config=prepared.model_config,
        effective_to=prepared.effective_to,
    )
    prepared_workbook_sha256 = sha256_file(workbook_path)
    if prepared_workbook_sha256 != prepared.build.rating_workbook_sha256:
        raise ValueError(
            "rating workbook changed during publication preparation: "
            f"expected={prepared.build.rating_workbook_sha256!r}, "
            f"actual={prepared_workbook_sha256!r}"
        )
    prepared = replace(
        prepared,
        build=bind_model_equivalence(
            prepared.build,
            calculated_sha256=tables.model_equivalence_sha256,
        ),
    )
    dialect_name = getattr(getattr(engine, "dialect", None), "name", None)
    if dialect_name == "sqlite":
        from pricing_pipeline.publishing.sqlite import publish_sqlite

        return publish_sqlite(engine, prepared, tables)

    from pricing_pipeline.publishing.sqlserver import publish_sqlserver

    return publish_sqlserver(engine, prepared, tables)
