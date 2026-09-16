"""Verify a SQL or artifact baseline and bind a dataframe to its declared roles.

The workflow calls these checks before reconstructing or fitting a model."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from superglm import SuperGLM

from pricing_pipeline.data.manifest import model_frame_evidence
from pricing_pipeline.modeling.monitoring.contracts import (
    PRIVATE_SUPERGLM_MONITORING_API,
    MonitoringError,
    _required_sha256,
)
from pricing_pipeline.publishing.metadata import (
    build_superglm_publication_receipt,
    canonical_receipt_bytes,
)
from pricing_pipeline.workbench.artifacts import (
    CandidateArtifactError,
    CandidateBundle,
    load_candidate_bundle,
)
from pricing_pipeline.workbench.core import Candidate, CandidateLineageError

if TYPE_CHECKING:
    from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline


def _verified_candidate_baseline(
    candidate: Candidate,
) -> tuple[SuperGLM, dict[str, Any], CandidateBundle]:
    try:
        refreshed = candidate.workbench.open(
            candidate.model_name,
            package_version=candidate.package_version,
        )
    except (CandidateArtifactError, CandidateLineageError, TypeError, ValueError) as exc:
        raise MonitoringError(
            "monitoring baseline candidate could not be refreshed from SQL"
        ) from exc
    if not isinstance(refreshed, Candidate):
        raise MonitoringError("monitoring baseline refresh did not return a Candidate")
    candidate = refreshed
    technical = candidate.technical
    if str(technical.get("package_status") or "").upper() != "PUBLISHED":
        raise MonitoringError("monitoring baseline candidate must be PUBLISHED")
    if str(technical.get("run_status") or "").upper() != "SUCCESS":
        raise MonitoringError("monitoring baseline candidate run must be SUCCESS")

    expected_identity = {
        "model_run_id": candidate.model_run_id,
        "rate_package_id": candidate.rate_package_id,
        "model_name": candidate.model_name,
    }
    for field_name, expected in expected_identity.items():
        if technical.get(field_name) != expected:
            raise MonitoringError(
                f"monitoring baseline candidate {field_name} does not match its SQL evidence"
            )
    current_rate_package_id = technical.get("current_rate_package_id")
    current_deployment_id = technical.get("current_deployment_id")
    if current_rate_package_id != candidate.rate_package_id or current_deployment_id is None:
        raise MonitoringError("monitoring baseline candidate is not the current deployment")

    try:
        bundle = load_candidate_bundle(
            technical.get("candidate_artifact_path"),
            expected_sha256=_required_sha256(
                technical.get("candidate_artifact_sha256"),
                "candidate_artifact_sha256",
            ),
            expected_size_bytes=int(technical.get("candidate_artifact_size_bytes")),
            expected_format=str(technical.get("candidate_artifact_format") or ""),
            expected_python_version=str(technical.get("candidate_python_version") or ""),
            expected_superglm_version=str(technical.get("candidate_superglm_version") or ""),
            allowed_root=candidate.workbench.settings.workbench_artifact_root,
        )
    except (CandidateArtifactError, TypeError, ValueError) as exc:
        raise MonitoringError(
            "monitoring baseline candidate artifact could not be re-verified"
        ) from exc
    if bundle.model_name != candidate.model_name:
        raise MonitoringError("monitoring baseline artifact model_name does not match SQL")
    if bundle.model_version != technical.get("model_version"):
        raise MonitoringError("monitoring baseline artifact model_version does not match SQL")
    if bundle.export_id != technical.get("export_id"):
        raise MonitoringError("monitoring baseline artifact export_id does not match SQL")
    if bundle.manifest_id != technical.get("manifest_id"):
        raise MonitoringError("monitoring baseline artifact manifest_id does not match SQL")
    if bundle.model_source_sha256 != technical.get("model_source_sha256"):
        raise MonitoringError("monitoring baseline artifact source digest does not match SQL")
    if bundle.model_frame_sha256 != technical.get("model_frame_sha256"):
        raise MonitoringError("monitoring baseline artifact frame digest does not match SQL")
    if bundle.split_set_id != technical.get("split_set_id"):
        raise MonitoringError("monitoring baseline artifact split_set_id does not match SQL")
    receipt_sha256 = _required_sha256(
        technical.get("publication_receipt_sha256"),
        "publication_receipt_sha256",
    )
    package_receipt_sha256 = _required_sha256(
        technical.get("package_publication_receipt_sha256"),
        "package_publication_receipt_sha256",
    )
    if receipt_sha256 != package_receipt_sha256:
        raise MonitoringError(
            "monitoring baseline run and package publication receipts do not match"
        )
    fitted_model = _require_fitted_superglm(bundle.fitted_model)
    try:
        rebuilt_receipt = build_superglm_publication_receipt(
            fitted_model,
            offset_contract=bundle.offset_contract,
            fit_sample_weight_name=bundle.fit_sample_weight_name,
            export_weight_name=bundle.export_weight_name,
            input_transforms=getattr(bundle, "input_transforms", None),
        )
    except (TypeError, ValueError) as exc:
        raise MonitoringError(
            "monitoring baseline candidate publication receipt could not be rebuilt"
        ) from exc
    rebuilt_receipt_sha256 = hashlib.sha256(canonical_receipt_bytes(rebuilt_receipt)).hexdigest()
    if rebuilt_receipt_sha256 != receipt_sha256 or rebuilt_receipt_sha256 != package_receipt_sha256:
        raise MonitoringError(
            "monitoring baseline candidate publication receipt does not match SQL lineage"
        )

    artifact_format = str(technical.get("candidate_artifact_format") or "").strip()
    python_version = str(technical.get("candidate_python_version") or "").strip()
    superglm_version = str(technical.get("candidate_superglm_version") or "").strip()
    deployment_slot = str(candidate.workbench.model_config.deployment_slot or "").strip()
    data_as_of_date = str(technical.get("data_as_of_date") or "").strip()
    for value, field_name in (
        (artifact_format, "candidate_artifact_format"),
        (python_version, "candidate_python_version"),
        (superglm_version, "candidate_superglm_version"),
        (deployment_slot, "deployment_slot"),
        (data_as_of_date, "data_as_of_date"),
    ):
        if not value:
            raise MonitoringError(f"monitoring baseline {field_name} is required")
    artifact_size = int(technical.get("candidate_artifact_size_bytes"))
    if artifact_size <= 0:
        raise MonitoringError("monitoring baseline candidate artifact size must be positive")

    baseline = {
        "candidate_artifact_format": artifact_format,
        "candidate_artifact_sha256": _required_sha256(
            technical.get("candidate_artifact_sha256"),
            "candidate_artifact_sha256",
        ),
        "candidate_artifact_size_bytes": artifact_size,
        "candidate_python_version": python_version,
        "candidate_superglm_version": superglm_version,
        "data_as_of_date": data_as_of_date,
        "deployment_id": int(current_deployment_id),
        "deployment_slot": deployment_slot,
        "export_id": bundle.export_id,
        "manifest_id": str(technical.get("manifest_id") or ""),
        "model_equivalence_sha256": _required_sha256(
            technical.get("model_equivalence_sha256"),
            "model_equivalence_sha256",
        ),
        "model_frame_sha256": _required_sha256(
            technical.get("model_frame_sha256"),
            "baseline model_frame_sha256",
        ),
        "model_id": int(technical.get("model_id")),
        "model_run_id": candidate.model_run_id,
        "model_source_sha256": _required_sha256(
            technical.get("model_source_sha256"),
            "model_source_sha256",
        ),
        "model_version": bundle.model_version,
        "package_version": int(candidate.package_version),
        "package_publication_receipt_sha256": receipt_sha256,
        "publication_receipt_sha256": receipt_sha256,
        "rate_package_id": candidate.rate_package_id,
        "row_order_sha256": _required_sha256(
            bundle.row_order_sha256,
            "row_order_sha256",
        ),
        "split_set_id": bundle.split_set_id,
    }
    return fitted_model, baseline, bundle


def _resolve_monitoring_baseline(
    value: SuperGLM | Candidate | SqlBaseline,
) -> tuple[SuperGLM | SqlBaseline, dict[str, Any] | None, CandidateBundle | SqlBaseline | None]:
    from pricing_pipeline.modeling.monitoring.snapshot import (
        SqlBaseline,
        restore_monitoring_snapshot,
    )

    if isinstance(value, SqlBaseline):
        # Recheck even a caller-created/replaced record before consuming its JSON.
        checked = restore_monitoring_snapshot(
            value.snapshot_json, expected_sha256=value.snapshot_sha256
        )
        if (
            value.identity is not None
            and value.identity.get("snapshot_sha256") != checked.snapshot_sha256
        ):
            raise MonitoringError(
                "SQL baseline identity does not match the snapshot used for monitoring"
            )
        checked = replace(
            checked, identity=None if value.identity is None else dict(value.identity)
        )
        return checked, checked.identity, checked
    if isinstance(value, Candidate):
        return _verified_candidate_baseline(value)
    return _require_fitted_superglm(value), None, None


def _ordered_series_matches(left: Any, right: pd.Series) -> bool:
    values = np.asarray(left)
    if values.ndim != 1 or len(values) != len(right):
        return False
    return pd.Series(values).reset_index(drop=True).equals(right.reset_index(drop=True))


def _bind_monitoring_model_frame(
    X: pd.DataFrame,
    y: Any,
    *,
    model_frame: pd.DataFrame | None,
    target_column: str | None,
    sample_weight: Any,
    fit_sample_weight_name: str | None,
    offset: Any,
    offset_column: str | None,
) -> str | None:
    if model_frame is None:
        if target_column is not None or offset_column is not None:
            raise MonitoringError("target_column and offset_column require the ordered model_frame")
        return None
    if not isinstance(model_frame, pd.DataFrame) or model_frame.empty:
        raise ValueError("model_frame must be a non-empty pandas DataFrame")
    if not isinstance(target_column, str) or not target_column.strip():
        raise MonitoringError("target_column is required with model_frame")
    target_name = target_column.strip()
    required_columns = [*X.columns, target_name]
    if sample_weight is not None:
        if not isinstance(fit_sample_weight_name, str) or not fit_sample_weight_name.strip():
            raise MonitoringError(
                "fit_sample_weight_name is required to bind sample_weight to model_frame"
            )
        required_columns.append(fit_sample_weight_name.strip())
    if offset is not None:
        if not isinstance(offset_column, str) or not offset_column.strip():
            raise MonitoringError("offset_column is required to bind offset to model_frame")
        required_columns.append(offset_column.strip())
    missing = [str(column) for column in required_columns if column not in model_frame.columns]
    if missing:
        raise MonitoringError(
            "ordered model frame is missing monitoring columns: " + ", ".join(missing)
        )
    if len(model_frame) != len(X):
        raise MonitoringError("X does not match the ordered model frame row count")
    actual_X = X.reset_index(drop=True)
    expected_X = model_frame.loc[:, list(X.columns)].reset_index(drop=True)
    if not actual_X.equals(expected_X):
        raise MonitoringError("X does not match the ordered model frame")
    if not _ordered_series_matches(y, model_frame[target_name]):
        raise MonitoringError("y does not match target_column in the ordered model frame")
    if sample_weight is not None:
        weight_name = str(fit_sample_weight_name).strip()
        if not _ordered_series_matches(sample_weight, model_frame[weight_name]):
            raise MonitoringError(
                "sample_weight does not match fit_sample_weight_name in the ordered model frame"
            )
    if offset is not None:
        resolved_offset_column = str(offset_column).strip()
        if not _ordered_series_matches(offset, model_frame[resolved_offset_column]):
            raise MonitoringError("offset does not match offset_column in the ordered model frame")
    return model_frame_evidence(model_frame)[0]


def _require_fitted_superglm(model: Any) -> SuperGLM:
    if not isinstance(model, SuperGLM):
        raise TypeError("monitoring requires a fitted SuperGLM model")
    try:
        _ = model.result
    except RuntimeError as exc:
        raise MonitoringError("monitoring requires a fitted SuperGLM model") from exc
    if not hasattr(model, "_config") or not isinstance(getattr(model, "_specs", None), dict):
        raise MonitoringError(
            "installed SuperGLM no longer exposes the pinned monitoring compatibility seam: "
            f"{PRIVATE_SUPERGLM_MONITORING_API}"
        )
    return model
