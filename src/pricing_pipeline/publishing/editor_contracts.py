"""Records and submission identity shared by the edit publication stages.

ParentCandidate is verified SQL/model input; EditorExport is the prepared child
build; EditorPublicationResult identifies the saved package. Policy metadata
checks retain the declared manual-adjustment intent."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pricing_pipeline.modeling.manual_adjustment import (
    ManualAdjustmentPolicy,
    manual_adjustment_policy_from_metadata,
)
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.identity import canonical_json
from pricing_pipeline.publishing.metadata import (
    SuperGLMPublicationReceipt,
)
from pricing_pipeline.workbench.artifacts import (
    CandidateBundle,
)
from pricing_pipeline.workbench.submission import (
    EditorSubmission,
    EditorSubmissionError,
)


@dataclass(frozen=True)
class ChampionSnapshot:
    """The currently deployed package and its model, or the reason that model is unavailable."""

    deployment_slot: str
    rate_package_id: int | None
    bundle: CandidateBundle | None
    unavailable_reason: str | None = None

    @property
    def status(self) -> str:
        if self.rate_package_id is None:
            return "NO_CHAMPION"
        if self.bundle is None:
            return "UNAVAILABLE"
        return "COMPARED"

    def revision_metadata(self) -> dict[str, Any]:
        return {
            "available": self.status == "COMPARED",
            "deployment_slot": self.deployment_slot,
            "rate_package_id": self.rate_package_id,
            "reason": self.unavailable_reason,
            "status": self.status,
        }


@dataclass(frozen=True)
class ParentCandidate:
    """The saved parent model, its SQL lineage and the champion snapshot used to review edits."""

    model_id: int
    model_name: str
    model_version: str
    package_version: int
    rate_package_id: int
    model_run_id: int
    effective_from: str | None
    effective_to: str | None
    config: ModelBuildConfig
    bundle: CandidateBundle
    champion: ChampionSnapshot


@dataclass(frozen=True)
class EditorExport:
    """Replayed edit output and artifacts ready to become a child publication request."""

    completed_build: ApprovedModelBuild
    publication_receipt: SuperGLMPublicationReceipt
    revision_metadata: dict[str, Any]
    edited_model: Any
    bundle: CandidateBundle


@dataclass(frozen=True)
class EditorPublicationResult:
    """The saved child package identity and whether publication reused an earlier result."""

    submission_id: str
    model_name: str
    parent_rate_package_id: int
    rate_package_id: int
    package_version: int
    model_run_id: int
    package_status: str
    was_existing: bool
    model_kind: str = "EDITOR_EDIT"
    deduplicated: bool = False


@dataclass(frozen=True)
class EditorPublicationAttempt:
    """Temporary and final artifact directories for one edit publication attempt."""

    staging_dir: Path
    final_dir: Path


_EDITED_MODEL_UNSET = object()


def _editor_export_id(submission: EditorSubmission) -> str:
    prefix = "manual" if _submission_model_kind(submission) == "MANUAL_EDIT" else "editor"
    return f"{prefix}__{submission.submission_id.replace('-', '_')}"


def _submission_model_kind(submission: EditorSubmission) -> str:
    return str(getattr(submission, "model_kind", "EDITOR_EDIT") or "EDITOR_EDIT").upper()


def _manual_policy_for_submission(
    submission: EditorSubmission,
) -> ManualAdjustmentPolicy | None:
    if _submission_model_kind(submission) != "MANUAL_EDIT":
        return None
    try:
        return manual_adjustment_policy_from_metadata(getattr(submission, "edit_metadata", None))
    except (TypeError, ValueError) as exc:
        raise EditorSubmissionError(
            f"MANUAL_EDIT submission has invalid manual adjustment policy: {exc}"
        ) from exc


def _manual_policy_provenance_identity(value: object) -> str | None:
    if not isinstance(value, Mapping):
        return None
    try:
        manual_adjustment_policy_from_metadata(value)
        return canonical_json(dict(value))
    except (TypeError, ValueError):  # fmt: skip
        return None
