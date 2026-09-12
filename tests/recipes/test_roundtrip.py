from dataclasses import replace

import numpy as np
import pytest
from sklearn.model_selection import GroupKFold, KFold, TimeSeriesSplit
from superglm import Categorical, Polynomial, Spline, SuperGLM

from pricing_pipeline import notebook as api
from pricing_pipeline.modeling.recipes import ModelRecipe
from pricing_pipeline.modeling.recipes.schema import RecipeError, UnsupportedRecipeError


def test_grouped_special_recipe_roundtrip(grouped_model_case, tmp_path):
    dataset, spec, glm = grouped_model_case
    original = ModelRecipe.from_model(glm, spec=spec)
    loaded = ModelRecipe.load(original.save(tmp_path / "model.toml"))
    rebuilt_spec, rebuilt = loaded.build(dataset=dataset)
    assert loaded.canonical_json == original.canonical_json
    assert ModelRecipe.from_model(rebuilt, spec=rebuilt_spec).sha256 == original.sha256
    assert rebuilt is not glm


@pytest.mark.parametrize("retain", [True, False])
def test_controlled_fit_and_fitted_prototype_parity(grouped_model_case, retain):
    dataset, spec, glm = grouped_model_case
    glm = SuperGLM(features=glm.features, selection_penalty=0.0, retain_fit_state=retain)
    original = ModelRecipe.from_model(glm, spec=spec)
    _, rebuilt = original.build(dataset=dataset)
    df = api.apply_transforms(dataset.df, spec.transforms)
    X, y = df[list(spec.features)], df[spec.target]
    glm.fit_reml(X, y, offset=df.log_exposure)
    rebuilt.fit_reml(X, y, offset=df.log_exposure)
    np.testing.assert_allclose(
        glm.predict(X, offset=df.log_exposure),
        rebuilt.predict(X, offset=df.log_exposure),
        rtol=1e-10,
    )
    assert ModelRecipe.from_model(glm, spec=spec).canonical_json == original.canonical_json


@pytest.mark.parametrize(
    "splitter", [KFold(3, shuffle=True, random_state=19), GroupKFold(3), TimeSeriesSplit(3)]
)
def test_splitter_membership(grouped_model_case, splitter):
    dataset, spec, glm = grouped_model_case
    groups_column = "region" if isinstance(splitter, GroupKFold) else None
    # Groups may be a feature in the existing Python splitter contract.
    spec = replace(spec, validation=splitter, groups_column=groups_column)
    rebuilt_spec, _ = ModelRecipe.from_model(glm, spec=spec).build(dataset=dataset)
    kwargs = {"groups": dataset.df.region} if groups_column else {}
    for before, after in zip(
        splitter.split(dataset.df, **kwargs),
        rebuilt_spec.validation.split(dataset.df, **kwargs),
        strict=True,
    ):
        for a, b in zip(before, after, strict=True):
            np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize(
    "feature",
    [
        Categorical(levels=[1, 2, 3], base=1, unseen="base"),
        Polynomial(powers=[1, 3]),
        Spline("ps", k=6),
        Spline("ns", k=4),
        Spline("bs", k=6),
        Spline("cr_cardinal", k=4),
    ],
)
def test_feature_constructor_roundtrip(grouped_model_case, feature):
    dataset, spec, _ = grouped_model_case
    spec = replace(spec, features=["x"])
    recipe = ModelRecipe.from_model(SuperGLM(features={"x": feature}), spec=spec)
    rebuilt_spec, rebuilt = recipe.build(dataset=dataset)
    assert (
        ModelRecipe.from_model(rebuilt, spec=rebuilt_spec).canonical_json == recipe.canonical_json
    )


def test_unknown_field_and_custom_splitter(grouped_model_case):
    _, spec, glm = grouped_model_case

    class Custom(KFold):
        pass

    with pytest.raises(UnsupportedRecipeError, match="validation.*Custom"):
        ModelRecipe.from_model(glm, spec=replace(spec, validation=Custom(3)))
    recipe = ModelRecipe.from_model(glm, spec=spec)
    data = recipe.document.to_dict()
    data["features"]["region"]["typo"] = True
    with pytest.raises(RecipeError, match="features.region.typo"):
        type(recipe.document)(**data)
