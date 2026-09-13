"""Load submitted edits and verify them by replaying the recorded intent.

Check manual policies and legacy editor sessions against the trusted parent.
Compare fitted runtime state as well as predictions before returning the model."""

from __future__ import annotations

import hashlib
import io
import pickle
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from pricing_pipeline.modeling.manual_adjustment import (
    ManualAdjustmentPolicy,
    replay_manual_adjustment_policy,
)
from pricing_pipeline.publishing.editor_contracts import (
    ParentCandidate,
    _manual_policy_for_submission,
)
from pricing_pipeline.publishing.metadata import (
    build_superglm_publication_receipt,
    canonical_receipt_bytes,
)
from pricing_pipeline.workbench.artifacts import (
    CandidateArtifactError,
    CandidateBundle,
    load_edited_model,
)
from pricing_pipeline.workbench.submission import (
    LEGACY_SUBMISSION_FORMAT,
    SUBMISSION_FORMAT,
    EditorSubmission,
    EditorSubmissionError,
    sha256_file,
)


def _load_edited_model(
    parent: ParentCandidate,
    submission: EditorSubmission,
    *,
    allowed_root: str | Path,
) -> Any:
    manual_policy = _manual_policy_for_submission(submission)
    submission_format = getattr(submission, "format", LEGACY_SUBMISSION_FORMAT)
    if submission_format == LEGACY_SUBMISSION_FORMAT:
        edited_model = _replay_legacy_editor_session(
            parent,
            submission,
            allowed_root=allowed_root,
        )
        if manual_policy is not None:
            _require_manual_policy_replay(parent, edited_model, manual_policy)
        return edited_model
    if submission_format != SUBMISSION_FORMAT:
        raise EditorSubmissionError(f"unsupported editor submission format {submission_format!r}")

    metadata = (
        submission.edited_model_path,
        submission.edited_model_sha256,
        submission.edited_model_size_bytes,
        submission.edited_model_format,
        submission.edited_model_python_version,
        submission.edited_model_superglm_version,
    )
    if any(value is None for value in metadata):
        raise EditorSubmissionError("v2 submission has incomplete edited model metadata")
    try:
        edited_model = load_edited_model(
            submission.edited_model_path,
            expected_sha256=submission.edited_model_sha256,
            expected_size_bytes=submission.edited_model_size_bytes,
            expected_format=submission.edited_model_format,
            expected_python_version=submission.edited_model_python_version,
            expected_superglm_version=submission.edited_model_superglm_version,
            allowed_root=allowed_root,
        )
    except CandidateArtifactError as exc:
        raise EditorSubmissionError(f"edited model artifact failed verification: {exc}") from exc

    if getattr(edited_model, "_result", None) is None:
        raise EditorSubmissionError("edited model artifact is not fitted")
    if not callable(getattr(edited_model, "predict", None)):
        raise EditorSubmissionError("edited model artifact has no callable predict method")
    try:
        parent_features = set(parent.bundle.fitted_model.features)
        edited_features = set(edited_model.features)
    except (AttributeError, TypeError) as exc:
        raise EditorSubmissionError("edited model has invalid feature names") from exc
    if edited_features != parent_features:
        raise EditorSubmissionError(
            "edited model feature names do not match the parent model: "
            f"parent={sorted(parent_features)!r}, edited={sorted(edited_features)!r}"
        )
    _predict(edited_model, parent.bundle)
    if manual_policy is not None:
        _require_manual_policy_replay(parent, edited_model, manual_policy)
    return edited_model


def _require_manual_policy_replay(
    parent: ParentCandidate,
    edited_model: Any,
    policy: ManualAdjustmentPolicy,
) -> None:
    try:
        _, trusted_model = replay_manual_adjustment_policy(parent.bundle, policy)
        expected = _predict(trusted_model, parent.bundle)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise EditorSubmissionError(
            "MANUAL_EDIT policy could not be replayed against the verified parent bundle"
        ) from exc
    actual = _predict(edited_model, parent.bundle)
    if not np.allclose(actual, expected, rtol=1e-10, atol=1e-12):
        raise EditorSubmissionError(
            "submitted MANUAL_EDIT model does not match trusted manual adjustment policy "
            "replay over the full verified parent model frame"
        )
    try:
        receipt_kwargs = {
            "offset_contract": parent.bundle.offset_contract,
            "fit_sample_weight_name": parent.bundle.fit_sample_weight_name,
            "export_weight_name": parent.bundle.export_weight_name,
            "input_transforms": getattr(parent.bundle, "input_transforms", None),
        }
        trusted_receipt = build_superglm_publication_receipt(
            trusted_model,
            **receipt_kwargs,
        )
        submitted_receipt = build_superglm_publication_receipt(
            edited_model,
            **receipt_kwargs,
        )
        receipts_match = canonical_receipt_bytes(submitted_receipt) == canonical_receipt_bytes(
            trusted_receipt
        )
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise EditorSubmissionError(
            "MANUAL_EDIT publication receipt could not be verified against the trusted "
            "policy replay"
        ) from exc
    if not receipts_match:
        raise EditorSubmissionError(
            "submitted MANUAL_EDIT publication receipt does not match trusted manual "
            "adjustment policy replay"
        )
    try:
        submitted_runtime_sha256 = _normalized_fitted_runtime_sha256(edited_model)
        trusted_runtime_sha256 = _normalized_fitted_runtime_sha256(trusted_model)
    except (EOFError, OSError, pickle.PickleError, TypeError, ValueError) as exc:
        raise EditorSubmissionError(
            "MANUAL_EDIT normalized fitted runtime state could not be verified"
        ) from exc
    if submitted_runtime_sha256 != trusted_runtime_sha256:
        raise EditorSubmissionError(
            "submitted MANUAL_EDIT normalized fitted runtime state does not match "
            "trusted manual adjustment policy replay"
        )


def _normalized_fitted_runtime_sha256(model: Any) -> str:
    artifact = io.BytesIO()
    joblib.dump(model, artifact, protocol=5)
    artifact.seek(0)
    normalized_model = joblib.load(artifact)
    normalized_pickle = pickle.dumps(normalized_model, protocol=5)
    return hashlib.sha256(normalized_pickle).hexdigest()


def _replay_legacy_editor_session(
    parent: ParentCandidate,
    submission: EditorSubmission,
    *,
    allowed_root: str | Path,
) -> Any:
    path = Path(submission.editor_session_path).expanduser().resolve()
    root = Path(allowed_root).expanduser().resolve()
    if not path.is_relative_to(root):
        raise EditorSubmissionError(f"editor session is outside artifact root {root}: {path}")
    if path.stat().st_size != int(submission.editor_session_size_bytes):
        raise EditorSubmissionError("editor session byte-size verification failed")
    if sha256_file(path) != submission.editor_session_sha256:
        raise EditorSubmissionError("editor session SHA-256 verification failed")
    from superglm.editor import EditorSession

    session = EditorSession.load(path, model=parent.bundle.fitted_model)
    return session.to_model(
        X=parent.bundle.X,
        y=parent.bundle.y,
        sample_weight=parent.bundle.sample_weight,
        offset=parent.bundle.offset,
    )


def _predict(model: Any, bundle: CandidateBundle) -> np.ndarray:
    if bundle.offset is None:
        prediction = model.predict(bundle.X)
    else:
        prediction = model.predict(bundle.X, offset=bundle.offset)
    values = np.asarray(prediction, dtype=float).reshape(-1)
    if len(values) != len(bundle.X) or not np.isfinite(values).all():
        raise EditorSubmissionError("model returned invalid training predictions")
    return values
