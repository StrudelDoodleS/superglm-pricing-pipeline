"""Publish an editor or manual-adjustment submission through explicit stages.

Validate the submission, resolve retries, load the parent, replay edits, export
a child build, then call the common publisher. Artifact attempt cleanup stays
with this workflow. Record types remain importable here for existing callers."""

from __future__ import annotations

import os
import shutil
from collections.abc import (
    Iterator,
)
from contextlib import (
    contextmanager,
)
from pathlib import (
    Path,
)
from typing import (
    Any,
)
from uuid import (
    uuid4,
)

from pricing_pipeline.infra.config import (
    Settings,
)
from pricing_pipeline.infra.file_lock import (
    exclusive_file_lock,
)
from pricing_pipeline.models.config import (
    ModelBuildConfig,
)
from pricing_pipeline.publishing.editor_contracts import (
    ChampionSnapshot,
    EditorExport,
    EditorPublicationAttempt,
    EditorPublicationResult,
    ParentCandidate,
    _manual_policy_for_submission,
)
from pricing_pipeline.publishing.editor_export import (
    export_edited_model,
    parent_cv_metrics,
    training_comparison_metrics,
)
from pricing_pipeline.publishing.editor_parent import (
    load_parent_candidate,
)
from pricing_pipeline.publishing.editor_replay import (
    _load_edited_model,
)
from pricing_pipeline.publishing.editor_retry import (
    _resolve_existing_editor_publication,
    _verify_reused_publication,
)
from pricing_pipeline.publishing.publish import (
    CompletedModelPublishResult,
    DraftVerification,
    PublicationRequest,
    publish_candidate,
)
from pricing_pipeline.workbench.submission import (
    EditorSubmission,
    EditorSubmissionError,
    load_verified_submission,
    sha256_file,
)


def publish_editor_submission(
    engine,
    *,
    settings: Settings,
    submission_path: str,
    submission_sha256: str,
    dag_id: str,
    airflow_run_id: str,
    created_by: str,
    model_config: ModelBuildConfig,
) -> EditorPublicationResult:
    """Verify proposed edits against their saved parent and publish a child package.

    Load the submission, replay the session or manual policy, export checked
    artifacts and pass a ``PublicationRequest`` to the common publisher.
    """

    publisher_identity = _publisher_identity(created_by)
    submission = _load_submission(
        submission_path=submission_path,
        submission_sha256=submission_sha256,
        allowed_root=settings.workbench_artifact_root,
    )
    _require_submission_config(submission, model_config)
    submission_dir = _submission_directory(
        submission,
        allowed_root=settings.workbench_artifact_root,
    )
    with _editor_publication_lock(submission_dir):
        existing = _resolve_existing_editor_publication(
            engine,
            submission,
            allowed_root=settings.workbench_artifact_root,
        )
        if existing is not None:
            return existing
        parent = load_parent_candidate(
            engine,
            submission,
            model_config=model_config,
            allowed_root=settings.workbench_artifact_root,
        )
        edited = _load_edited_model(
            parent,
            submission,
            allowed_root=settings.workbench_artifact_root,
        )
        with _publication_attempt(
            submission,
            settings.workbench_artifact_root,
        ) as attempt:
            exported = _export_edited_build(
                submission=submission,
                parent=parent,
                edited_model=edited,
                created_by=publisher_identity,
                attempt=attempt,
                allowed_root=settings.workbench_artifact_root,
            )
            request = _publication_request(
                submission=submission,
                parent=parent,
                exported=exported,
                model_config=model_config,
                execution_name=dag_id,
                execution_id=airflow_run_id,
                allowed_root=settings.workbench_artifact_root,
            )
            publication = publish_candidate(engine, request)
            reused_parent_rate_package_id = _verify_reused_publication(
                engine=engine,
                submission=submission,
                publication=publication,
                allowed_root=settings.workbench_artifact_root,
            )
            if publication.was_existing or publication.deduplicated:
                _remove_path(attempt.final_dir)
            return _editor_result(
                submission=submission,
                publication=publication,
                parent_rate_package_id=reused_parent_rate_package_id,
            )


def _publisher_identity(value: str) -> str:
    identity = str(value).strip()
    if not identity:
        raise EditorSubmissionError("publisher identity is required")
    return identity


def _load_submission(
    *,
    submission_path: str,
    submission_sha256: str,
    allowed_root: str | Path,
) -> EditorSubmission:
    submission = load_verified_submission(
        submission_path,
        submission_sha256,
        allowed_root=allowed_root,
    )
    _manual_policy_for_submission(submission)
    return submission


def _require_submission_config(
    submission: EditorSubmission,
    model_config: ModelBuildConfig,
) -> None:
    submitted_slot = str(submission.deployment_slot or "").strip().upper()
    configured_slot = str(model_config.deployment_slot or "").strip().upper()
    if not submitted_slot or submitted_slot != configured_slot:
        raise EditorSubmissionError(
            "explicit model config deployment_slot does not match the editor submission"
        )


@contextmanager
def _publication_attempt(
    submission: EditorSubmission,
    allowed_root: str | Path,
) -> Iterator[EditorPublicationAttempt]:
    submission_dir = _submission_directory(
        submission,
        allowed_root=allowed_root,
    )
    _remove_unpublished_editor_attempts(submission_dir)
    attempt = _new_editor_publication_attempt(submission_dir)
    try:
        yield attempt
    except BaseException:
        _remove_path(attempt.final_dir)
        raise
    finally:
        _remove_path(attempt.staging_dir)


def _export_edited_build(
    *,
    submission: EditorSubmission,
    parent: ParentCandidate,
    edited_model: Any,
    created_by: str,
    attempt: EditorPublicationAttempt,
    allowed_root: str | Path,
) -> EditorExport:
    exported = export_edited_model(
        parent,
        submission,
        created_by=created_by,
        allowed_root=allowed_root,
        write_dir=attempt.staging_dir,
        published_dir=attempt.final_dir,
        edited_model=edited_model,
    )
    os.rename(attempt.staging_dir, attempt.final_dir)
    build = exported.completed_build
    if sha256_file(build.rating_workbook_path) != build.rating_workbook_sha256:
        raise EditorSubmissionError("edited rating workbook SHA-256 changed before publication")
    return exported


def _publication_request(
    *,
    submission: EditorSubmission,
    parent: ParentCandidate,
    exported: EditorExport,
    model_config: ModelBuildConfig,
    execution_name: str,
    execution_id: str,
    allowed_root: str | Path,
) -> PublicationRequest:
    return PublicationRequest(
        build=exported.completed_build,
        model_config=model_config,
        execution_name=execution_name,
        execution_id=execution_id,
        allowed_artifact_root=Path(allowed_root).expanduser().resolve(),
        effective_to=parent.effective_to,
        parent_rate_package_id=submission.parent_rate_package_id,
        parent_model_run_id=submission.parent_model_run_id,
        revision_metadata={
            **exported.revision_metadata,
            "published_by": exported.completed_build.created_by,
        },
        verification=DraftVerification(
            model=exported.edited_model,
            bundle=exported.bundle,
            receipt=exported.publication_receipt,
        ),
    )


def _editor_result(
    *,
    submission: EditorSubmission,
    publication: CompletedModelPublishResult,
    parent_rate_package_id: int | None,
) -> EditorPublicationResult:
    if publication.model_run_id is None:
        raise RuntimeError("package publication did not record editor lineage")
    return EditorPublicationResult(
        submission_id=submission.submission_id,
        model_name=publication.model_name,
        parent_rate_package_id=(
            submission.parent_rate_package_id
            if parent_rate_package_id is None
            else parent_rate_package_id
        ),
        rate_package_id=publication.rate_package_id,
        package_version=publication.package_version,
        model_run_id=publication.model_run_id,
        package_status=publication.package_status,
        was_existing=publication.was_existing,
        model_kind=publication.model_kind,
        deduplicated=publication.deduplicated,
    )


def _submission_directory(
    submission: EditorSubmission,
    *,
    allowed_root: str | Path,
) -> Path:
    root = Path(allowed_root).expanduser().resolve()
    submission_path = Path(submission.path).expanduser().resolve()
    if not submission_path.is_relative_to(root):
        raise EditorSubmissionError(
            f"submission path is outside configured artifact root {root}: {submission_path}"
        )
    return submission_path.parent


@contextmanager
def _editor_publication_lock(submission_dir: Path) -> Iterator[None]:
    lock_path = submission_dir / "publication.lock"
    with exclusive_file_lock(lock_path):
        yield


def _remove_unpublished_editor_attempts(submission_dir: Path) -> None:
    published_root = submission_dir / "published"
    for root_name in (".staging", "attempts"):
        root = published_root / root_name
        if not root.is_dir():
            continue
        for child in root.iterdir():
            _remove_path(child)


def _new_editor_publication_attempt(submission_dir: Path) -> EditorPublicationAttempt:
    attempt_id = uuid4().hex
    published_root = submission_dir / "published"
    staging_root = published_root / ".staging"
    attempts_root = published_root / "attempts"
    staging_root.mkdir(parents=True, exist_ok=True)
    attempts_root.mkdir(parents=True, exist_ok=True)
    staging_dir = staging_root / attempt_id
    final_dir = attempts_root / attempt_id
    staging_dir.mkdir()
    return EditorPublicationAttempt(staging_dir=staging_dir, final_dir=final_dir)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


__all__ = [
    "ChampionSnapshot",
    "EditorExport",
    "EditorPublicationAttempt",
    "EditorPublicationResult",
    "ParentCandidate",
    "export_edited_model",
    "load_parent_candidate",
    "parent_cv_metrics",
    "publish_editor_submission",
    "training_comparison_metrics",
]
