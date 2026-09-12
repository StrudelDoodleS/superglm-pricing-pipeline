from dataclasses import replace

import pytest
from sklearn.model_selection import KFold

from pricing_pipeline import notebook as api
from pricing_pipeline.modeling.recipes import ModelRecipe, UnsupportedRecipeError
from pricing_pipeline.workbench.artifacts import load_candidate_bundle



def test_snapshot_survives_original_mutation(fitted_case, tmp_path):
    _, model, candidate, glm = fitted_case
    before = candidate.recipe.sha256
    glm.selection_penalty = 0.3
    object.__setattr__(model.spec, "scoring", ("deviance",))
    assert candidate.recipe.sha256 == before
    assert ModelRecipe.load(candidate.recipe.save(tmp_path / "fit.toml")).sha256 == before
    build = candidate.completed_build
    assert build.recipe_status == "CAPTURED"
    bundle = load_candidate_bundle(
        build.candidate_artifact_path,
        expected_sha256=build.candidate_artifact_sha256,
        expected_size_bytes=build.candidate_artifact_size_bytes,
        expected_format=build.candidate_artifact_format,
        expected_python_version=build.candidate_python_version,
        expected_superglm_version=build.candidate_superglm_version,
        allowed_root=tmp_path,
    )
    assert bundle.recipe_capture == build.recipe_capture


def test_python_override_is_captured(grouped_model_case, tmp_path):
    dataset, spec, glm = grouped_model_case
    initial = ModelRecipe.from_model(glm, spec=spec)
    glm.lambda2 = 0.5
    expected = ModelRecipe.from_model(glm, spec=spec)
    assert initial.sha256 != expected.sha256
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    (tmp_path / "definition.py").write_text("# model definition\n")
    model = api.register_model(pricing, spec, source_root=tmp_path)
    try:
        candidate = api.fit_model(
            pricing,
            model=model,
            frame=api.apply_transforms(dataset.df, spec.transforms),
            superglm_model=glm,
        )
        assert candidate.recipe.sha256 == expected.sha256
    finally:
        pricing.engine.dispose()


def test_unsupported_splitter_still_fits(grouped_model_case, tmp_path):
    class BusinessSplit(KFold):
        pass

    dataset, spec, glm = grouped_model_case
    spec = replace(spec, validation=BusinessSplit(3))
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    (tmp_path / "definition.py").write_text("# model definition\n")
    model = api.register_model(pricing, spec, source_root=tmp_path)
    try:
        with pytest.warns(UserWarning, match="recipe.*unsupported|unsupported.*recipe"):
            candidate = api.fit_model(
                pricing,
                model=model,
                frame=api.apply_transforms(dataset.df, spec.transforms),
                superglm_model=glm,
            )
        assert candidate.completed_build.recipe_status == "UNSUPPORTED"
        with pytest.raises(UnsupportedRecipeError, match="BusinessSplit"):
            candidate.recipe.save(tmp_path / "unsupported.toml")
    finally:
        pricing.engine.dispose()
