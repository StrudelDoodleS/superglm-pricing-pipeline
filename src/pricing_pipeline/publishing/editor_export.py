"""Export a verified edited model and compare it with its parent and champion.

Write the workbook, receipt and bundle into the attempt directory; return
EditorExport with final artifact paths and the parent training lineage."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import mean_poisson_deviance

from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing.editor_contracts import (
    _EDITED_MODEL_UNSET,
    EditorExport,
    ParentCandidate,
    _editor_export_id,
    _submission_model_kind,
)
from pricing_pipeline.publishing.editor_replay import _load_edited_model, _predict
from pricing_pipeline.publishing.metadata import (
    build_superglm_publication_receipt,
    write_publication_receipt,
)
from pricing_pipeline.publishing.rating_tables import export_rating_tables
from pricing_pipeline.workbench.artifacts import (
    CandidateArtifactMetadata,
    CandidateBundle,
    save_candidate_bundle,
)
from pricing_pipeline.workbench.submission import (
    LEGACY_SUBMISSION_FORMAT,
    SUBMISSION_FORMAT,
    EditorSubmission,
    EditorSubmissionError,
    sha256_file,
)


def _mean_model_deviance(
    model: Any,
    y: np.ndarray,
    prediction: np.ndarray,
    weights: np.ndarray,
) -> float | None:
    distribution = getattr(model, "_distribution", None)
    deviance_unit = getattr(distribution, "deviance_unit", None)
    if callable(deviance_unit):
        unit_values = np.asarray(deviance_unit(y, prediction), dtype=float)
        if unit_values.shape != y.shape or not np.isfinite(unit_values).all():
            raise EditorSubmissionError("model distribution returned invalid unit deviance")
        return float(np.average(unit_values, weights=weights))
    if np.all(y >= 0) and np.all(prediction > 0):
        return float(mean_poisson_deviance(y, prediction, sample_weight=weights))
    return None


def training_comparison_metrics(
    baseline_model: Any,
    edited_model: Any,
    bundle: CandidateBundle,
    *,
    comparison_name: str,
) -> tuple[dict[str, float], dict[str, str]]:
    name = str(comparison_name).strip().lower()
    if not name:
        raise ValueError("comparison_name is required")
    baseline = _predict(baseline_model, bundle)
    edited = _predict(edited_model, bundle)
    weights = (
        np.ones(len(bundle.X), dtype=float)
        if bundle.sample_weight is None
        else np.asarray(bundle.sample_weight, dtype=float)
    )
    if len(weights) != len(bundle.X) or not np.isfinite(weights).all() or weights.sum() <= 0:
        raise EditorSubmissionError("training comparison weights are invalid")
    absolute_delta = np.abs(edited - baseline)
    relative_delta = absolute_delta / np.maximum(np.abs(baseline), 1e-12)
    prefix = f"editor_training_{name}"
    metrics = {
        f"{prefix}_mean_absolute_prediction_delta": float(
            np.average(absolute_delta, weights=weights)
        ),
        f"{prefix}_max_absolute_prediction_delta": float(np.max(absolute_delta)),
        f"{prefix}_mean_absolute_relative_change": float(
            np.average(relative_delta, weights=weights)
        ),
    }
    y = np.asarray(bundle.y, dtype=float)
    if len(y) == len(bundle.X) and np.isfinite(y).all():
        baseline_deviance = _mean_model_deviance(
            baseline_model,
            y,
            baseline,
            weights,
        )
        edited_deviance = _mean_model_deviance(
            edited_model,
            y,
            edited,
            weights,
        )
    else:
        baseline_deviance = None
        edited_deviance = None
    if baseline_deviance is not None and edited_deviance is not None:
        metrics[f"{prefix}_baseline_deviance"] = baseline_deviance
        metrics[f"{prefix}_edited_deviance"] = edited_deviance
        delta_name = (
            "editor_training_deviance_delta" if name == "parent" else f"{prefix}_deviance_delta"
        )
        metrics[delta_name] = edited_deviance - baseline_deviance
    scope = f"editor_training_{name}"
    return metrics, {metric_name: scope for metric_name in metrics}


def parent_cv_metrics(
    bundle: CandidateBundle,
) -> dict[str, float]:
    report = bundle.cv_report
    metrics: dict[str, float] = {}
    for report_name, metric_prefix in (
        ("mean_scores", "cv_mean"),
        ("pooled_scores", "cv_pooled"),
        ("std_scores", "cv_std"),
    ):
        values = report.get(report_name) or {}
        for metric_name, raw_value in values.items():
            value = float(raw_value)
            if not math.isfinite(value):
                raise EditorSubmissionError(
                    f"parent CV metric {report_name}.{metric_name} is not finite"
                )
            metrics[f"{metric_prefix}_{metric_name}"] = value
    if report.get("oof_coverage") is not None:
        coverage = float(report["oof_coverage"])
        if not math.isfinite(coverage):
            raise EditorSubmissionError("parent CV OOF coverage is not finite")
        metrics["cv_oof_coverage"] = coverage
    return metrics


def export_edited_model(
    parent: ParentCandidate,
    submission: EditorSubmission,
    *,
    created_by: str,
    allowed_root: str | Path,
    write_dir: str | Path,
    published_dir: str | Path,
    edited_model: Any = _EDITED_MODEL_UNSET,
) -> EditorExport:
    if edited_model is _EDITED_MODEL_UNSET:
        edited_model = _load_edited_model(parent, submission, allowed_root=allowed_root)
    root = Path(allowed_root).expanduser().resolve()
    output_dir = Path(write_dir).expanduser().resolve()
    final_dir = Path(published_dir).expanduser().resolve()
    if not output_dir.is_relative_to(root) or not final_dir.is_relative_to(root):
        raise EditorSubmissionError("editor publication attempt is outside artifact root")
    if not output_dir.is_dir():
        raise EditorSubmissionError("editor publication staging directory does not exist")
    workbook_write_path = output_dir / "rating_tables.xlsx"
    workbook_path = final_dir / "rating_tables.xlsx"
    contract = parent.bundle.offset_contract
    export_options: dict[str, Any] = {}
    if parent.bundle.offset is not None:
        export_options["offset"] = parent.bundle.offset
    if contract.handling == "EXPORTED_FACTOR":
        export_options.update(
            offset_source=parent.bundle.offset_source,
            offset_name=contract.source_factor_name,
            offset_kind="auto",
        )
    export_rating_tables(
        edited_model,
        parent.bundle.X,
        parent.bundle.y,
        parent.bundle.export_weight,
        output_path=workbook_write_path,
        input_transforms=getattr(parent.bundle, "input_transforms", None),
        continuous_kind=parent.bundle.continuous_kind,
        **export_options,
    )
    workbook_sha256 = sha256_file(workbook_write_path)
    receipt = build_superglm_publication_receipt(
        edited_model,
        offset_contract=contract,
        fit_sample_weight_name=parent.bundle.fit_sample_weight_name,
        export_weight_name=parent.bundle.export_weight_name,
        input_transforms=getattr(parent.bundle, "input_transforms", None),
    )
    receipt_write_path = output_dir / "publication_receipt.json"
    receipt_path = final_dir / "publication_receipt.json"
    receipt_sha256 = write_publication_receipt(receipt, receipt_write_path)

    baseline_cv_metrics = parent_cv_metrics(parent.bundle)
    metrics, metric_scopes = training_comparison_metrics(
        parent.bundle.fitted_model,
        edited_model,
        parent.bundle,
        comparison_name="parent",
    )
    champion_bundle = parent.champion.bundle
    if champion_bundle is not None:
        champion_metrics, champion_scopes = training_comparison_metrics(
            champion_bundle.fitted_model,
            edited_model,
            parent.bundle,
            comparison_name="champion",
        )
        metrics.update(champion_metrics)
        metric_scopes.update(champion_scopes)
    champion_comparison = parent.champion.revision_metadata()
    edited_bundle = replace(
        parent.bundle,
        fitted_model=edited_model,
        cv_report={},
        model_name=parent.model_name,
        model_version=parent.model_version,
        export_id=_editor_export_id(submission),
    )
    artifact: CandidateArtifactMetadata = save_candidate_bundle(
        edited_bundle,
        output_dir / "candidate_bundle.joblib",
    )
    artifact = replace(
        artifact,
        path=str(final_dir / "candidate_bundle.joblib"),
    )
    revision_metadata = {
        "kind": (
            "SUPERGLM_MANUAL_EDIT"
            if _submission_model_kind(submission) == "MANUAL_EDIT"
            else "SUPERGLM_EDITOR"
        ),
        "schema_version": 1,
        "submission_id": submission.submission_id,
        "reason": submission.reason,
        "claimed_identity": submission.claimed_identity,
        "parent_rate_package_id": submission.parent_rate_package_id,
        "parent_model_run_id": submission.parent_model_run_id,
        "submission_path": submission.path,
        "submission_sha256": submission.sha256,
        "editor_session_path": submission.editor_session_path,
        "editor_session_sha256": submission.editor_session_sha256,
        "editor_session_size_bytes": submission.editor_session_size_bytes,
        "baseline_candidate_sha256": submission.baseline_candidate_sha256,
        "baseline_cv_metrics": baseline_cv_metrics,
        "comparison_metrics": {
            name: value for name, value in metrics.items() if name.startswith("editor_training_")
        },
        "champion_comparison": champion_comparison,
    }
    edit_metadata = getattr(submission, "edit_metadata", None)
    if edit_metadata is not None:
        revision_metadata["edit_metadata"] = edit_metadata
    if getattr(submission, "format", LEGACY_SUBMISSION_FORMAT) == SUBMISSION_FORMAT:
        revision_metadata.update(
            edited_model_path=submission.edited_model_path,
            edited_model_sha256=submission.edited_model_sha256,
            edited_model_size_bytes=submission.edited_model_size_bytes,
            edited_model_format=submission.edited_model_format,
            edited_model_python_version=submission.edited_model_python_version,
            edited_model_superglm_version=submission.edited_model_superglm_version,
        )
    completed_build = ApprovedModelBuild(
        recipe_capture=edited_bundle.recipe_capture,
        model_id=parent.model_id,
        model_name=parent.model_name,
        model_version=parent.model_version,
        model_type=parent.config.model_type,
        model_kind=_submission_model_kind(submission),
        target_name=parent.config.target_name,
        deployment_slot=submission.deployment_slot,
        manifest_id=submission.manifest_id,
        split_set_id=submission.split_set_id,
        export_id=_editor_export_id(submission),
        rating_workbook_path=str(workbook_path),
        rating_workbook_sha256=workbook_sha256,
        effective_from=parent.effective_from,
        created_by=created_by,
        publication_receipt_path=str(receipt_path),
        publication_receipt_sha256=receipt_sha256,
        candidate_artifact_path=artifact.path,
        candidate_artifact_sha256=artifact.sha256,
        candidate_artifact_format=artifact.format,
        candidate_artifact_size_bytes=artifact.size_bytes,
        candidate_python_version=artifact.python_version,
        candidate_superglm_version=artifact.superglm_version,
        model_source_sha256=submission.model_source_sha256,
        model_frame_sha256=edited_bundle.model_frame_sha256,
        metrics=metrics,
        metric_scopes=metric_scopes,
    )
    return EditorExport(
        completed_build=completed_build,
        publication_receipt=receipt,
        revision_metadata=revision_metadata,
        edited_model=edited_model,
        bundle=edited_bundle,
    )
