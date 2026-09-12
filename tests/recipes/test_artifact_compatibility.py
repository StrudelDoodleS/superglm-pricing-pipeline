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


def test_recipe_remains_verified_after_remote_equivalence_cleanup(
    fitted_case, tmp_path, monkeypatch
):
    from pricing_pipeline import notebook as api
    from pricing_pipeline.modeling.recipes import ModelRecipe
    from pricing_pipeline.orchestration.publish_completed_build import (
        _discard_redundant_completed_build_attempt,
    )

    pricing, model, first, glm = fitted_case
    saved = api.save_model_version(pricing, first)
    incoming = api.fit_model(
        pricing,
        model=model,
        frame=api.apply_transforms(model.spec.dataset.df, model.spec.transforms),
        superglm_model=glm,
    )
    canonical_result = replace(saved, was_existing=True, deduplicated=True)
    from pathlib import Path

    artifact = Path(incoming.completed_build.candidate_artifact_path)

    def publish(engine, *, completed_build, settings, **kwargs):
        _discard_redundant_completed_build_attempt(
            completed_build,
            publish_result=canonical_result,
            artifact_root=settings.workbench_artifact_root,
        )
        assert not artifact.exists()
        return canonical_result

    monkeypatch.setattr(api, "publish_completed_model_build", publish)
    assert api.save_model_version(replace(pricing, mode="remote"), incoming) is canonical_result
    exported = incoming.recipe.save(tmp_path / "after-save.toml")
    assert ModelRecipe.load(exported).sha256 == incoming.completed_build.recipe_sha256
    # Retained evidence cannot conceal a newly present but corrupt artifact.
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"tampered")
    with pytest.raises(CandidateArtifactError):
        _ = incoming.recipe


def test_remote_save_does_not_retain_unverified_recipe(fitted_case, monkeypatch):
    from pathlib import Path

    from pricing_pipeline import notebook as api

    pricing, _, candidate, _ = fitted_case
    Path(candidate.completed_build.candidate_artifact_path).write_bytes(b"tampered")
    monkeypatch.setattr(
        api,
        "publish_completed_model_build",
        lambda *a, **k: pytest.fail("published unverified recipe"),
    )
    with pytest.raises(CandidateArtifactError):
        api.save_model_version(replace(pricing, mode="remote"), candidate)
    with pytest.raises(CandidateArtifactError):
        _ = candidate.recipe


def test_missing_artifact_without_legitimate_cleanup_has_no_recipe_fallback(fitted_case):
    from pathlib import Path

    _, _, candidate, _ = fitted_case
    Path(candidate.completed_build.candidate_artifact_path).unlink()
    with pytest.raises(CandidateArtifactError):
        _ = candidate.recipe
