from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.metadata import SuperGLMPublicationReceipt
from pricing_pipeline.workbench.artifacts import CandidateBundle


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
