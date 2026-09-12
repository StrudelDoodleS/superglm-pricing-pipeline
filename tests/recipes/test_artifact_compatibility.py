import hashlib
from dataclasses import replace

import joblib
import pytest

from pricing_pipeline.workbench.artifacts import CandidateArtifactError, load_candidate_bundle


def _load(build, path, format, root):
    return load_candidate_bundle(
        path,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        expected_size_bytes=path.stat().st_size,
        expected_format=format,
        expected_python_version=build.candidate_python_version,
        expected_superglm_version=build.candidate_superglm_version,
        allowed_root=root,
    )


def test_v2_does_not_invent_recipe(fitted_case, tmp_path):
    _, _, candidate, _ = fitted_case
    build = candidate.completed_build
    envelope = joblib.load(build.candidate_artifact_path)
    envelope["format"] = "superglm-candidate-joblib-v2"
    envelope["bundle"] = replace(envelope["bundle"], recipe_capture=None)
    path = tmp_path / "old.joblib"
    joblib.dump(envelope, path)
    bundle = _load(build, path, envelope["format"], tmp_path)
    assert bundle.recipe_capture.status == "LEGACY"


def test_v3_capture_checksum_is_validated_after_unpickle(fitted_case, tmp_path):
    _, _, candidate, _ = fitted_case
    build = candidate.completed_build
    envelope = joblib.load(build.candidate_artifact_path)
    object.__setattr__(envelope["bundle"].recipe_capture, "sha256", "0" * 64)
    path = tmp_path / "tampered.joblib"
    joblib.dump(envelope, path)
    with pytest.raises(CandidateArtifactError, match="recipe|checksum"):
        _load(build, path, build.candidate_artifact_format, tmp_path)


def test_legacy_candidate_without_artifact_has_clear_recipe_error(fitted_case):
    from dataclasses import replace

    from pricing_pipeline.modeling.recipes import RecipeCapture, UnsupportedRecipeError

    _, _, candidate, _ = fitted_case
    legacy = replace(
        candidate,
        completed_build=candidate.completed_build.model_copy(
            update={"candidate_artifact_path": None, "recipe_capture": RecipeCapture()}
        ),
    )
    with pytest.raises(UnsupportedRecipeError, match="recipe unavailable.*artifact"):
        _ = legacy.recipe
