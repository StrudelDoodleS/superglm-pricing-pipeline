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


@pytest.mark.parametrize("missing", ["special", "declared"])
def test_absent_declared_levels_and_specials_keep_policy(grouped_model_case, missing):
    dataset, spec, glm = grouped_model_case
    df = api.apply_transforms(dataset.df, spec.transforms)
    if missing == "special":
        train = df[df.bonus_malus != "Unknown"]
    else:
        train = df[df.region != "C"]
    recipe = ModelRecipe.from_model(glm, spec=spec)
    _, rebuilt = recipe.build(dataset=dataset)
    X = df[list(spec.features)]
    for model in (glm, rebuilt):
        model.fit_reml(train[list(spec.features)], train[spec.target], offset=train.log_exposure)
    np.testing.assert_allclose(
        glm.predict(X, offset=df.log_exposure),
        rebuilt.predict(X, offset=df.log_exposure),
        rtol=1e-10,
    )
    unseen = X.copy()
    unseen.loc[0, "region"] = "UNSEEN"
    for model in (glm, rebuilt):
        with pytest.raises(ValueError, match="unseen|unknown|Unknown|not.*group|Unseen"):
            model.predict(unseen)


def test_cv_losses_match(grouped_model_case):
    from superglm import cross_validate

    dataset, spec, glm = grouped_model_case
    recipe = ModelRecipe.from_model(glm, spec=spec)
    _, rebuilt = recipe.build(dataset=dataset)
    df = api.apply_transforms(dataset.df, spec.transforms)
    options = {
        "cv": KFold(3, shuffle=True, random_state=11),
        "fit_mode": "fit_reml",
        "scoring": ["deviance"],
        "offset": df.log_exposure,
    }
    first = cross_validate(glm, df[list(spec.features)], df[spec.target], **options)
    second = cross_validate(rebuilt, df[list(spec.features)], df[spec.target], **options)
    np.testing.assert_allclose(
        first.fold_scores["deviance"], second.fold_scores["deviance"], rtol=1e-10
    )


def test_numeric_ordered_domains_and_specials_roundtrip(grouped_model_case):
    from superglm import OrderedCategorical

    dataset, spec, _ = grouped_model_case
    spec = replace(spec, features=["x"])
    feature = OrderedCategorical(
        values={1: 0.0, 2: 2.0, 3: 4.0, 4: 6.0}, specials=[9], base=1, basis=Spline("cr", k=3)
    )
    recipe = ModelRecipe.from_model(SuperGLM(features={"x": feature}), spec=spec)
    values = recipe.document.features["x"]["values"]
    assert (
        type(values[0]["level"]) is int
        and type(recipe.document.features["x"]["specials"][0]) is int
    )
    rebuilt_spec, rebuilt = recipe.build(dataset=dataset)
    assert ModelRecipe.from_model(rebuilt, spec=rebuilt_spec).sha256 == recipe.sha256


@pytest.mark.parametrize(
    "override",
    [
        {"family": __import__("superglm").Tweedie(p=1.5)},
        {"family": __import__("superglm").NegativeBinomial(theta=2.0)},
        {"penalty": __import__("superglm.penalties", fromlist=["Ridge"]).Ridge(lambda1=0.1)},
        {"link": __import__("superglm.links", fromlist=["PowerLink"]).PowerLink(power=0.5)},
    ],
)
def test_parameterized_estimator_objects(grouped_model_case, override):
    dataset, spec, glm = grouped_model_case
    model = SuperGLM(features=glm.features, **override)
    recipe = ModelRecipe.from_model(model, spec=spec)
    new_spec, rebuilt = recipe.build(dataset=dataset)
    assert ModelRecipe.from_model(rebuilt, spec=new_spec).canonical_json == recipe.canonical_json


def test_explicit_knots_boundary_policy_and_constraint_survive_fitting(
    grouped_model_case, tmp_path
):
    from superglm import Constraint, LambdaPolicy

    dataset, spec, _ = grouped_model_case
    spec = replace(spec, features=("x",), fit_mode="fit_reml")
    feature = Spline(
        "ps",
        knots=[1.0, 2.0, 3.0, 4.0],
        boundary=(0.0, 5.0),
        constraint=Constraint.postfit.increasing,
        lambda_policy=LambdaPolicy(mode="fixed", value=0.4),
    )
    glm = SuperGLM(features={"x": feature}, selection_penalty=0.0, retain_fit_state=False)
    recipe = ModelRecipe.from_model(glm, spec=spec)
    rebuilt_spec, rebuilt = ModelRecipe.load(recipe.save(tmp_path / "explicit.toml")).build(
        dataset=dataset
    )
    declaration = recipe.document.to_dict()["features"]["x"]
    assert declaration["knots"] == [1.0, 2.0, 3.0, 4.0]
    assert declaration["boundary"] == [0.0, 5.0]
    assert declaration["lambda_policy"] == {"mode": "fixed", "value": 0.4}
    df = api.apply_transforms(dataset.df, spec.transforms)
    for model in (glm, rebuilt):
        model.fit_reml(df[["x"]], df.claim_count, offset=df.log_exposure)
    np.testing.assert_allclose(
        glm.predict(df[["x"]], offset=df.log_exposure),
        rebuilt.predict(df[["x"]], offset=df.log_exposure),
        rtol=1e-10,
    )
    assert ModelRecipe.from_model(glm, spec=spec).sha256 == recipe.sha256
    assert ModelRecipe.from_model(rebuilt, spec=rebuilt_spec).sha256 == recipe.sha256


def test_typed_special_domain_labels_survive_public_roundtrip(grouped_model_case, tmp_path):
    import pandas as pd
    from superglm import OrderedCategorical

    dataset, spec, _ = grouped_model_case
    df = dataset.df.copy()
    df["x"] = pd.Series(["A", "B", "C", "D", 9.0] * 84, dtype=object)
    dataset = api.PricingDataset(
        df, name=dataset.name, source=dataset.source, key="id", as_of="as_of"
    )
    spec = replace(spec, dataset=dataset, features=("x",))
    glm = SuperGLM(
        features={
            "x": OrderedCategorical(
                order=["A", "B", "C", "D", 9.0], specials=[9], base="A", basis=Spline("cr", k=3)
            )
        },
        selection_penalty=0.0,
        retain_fit_state=False,
    )
    recipe = ModelRecipe.from_model(glm, spec=spec)
    path = recipe.save(tmp_path / "typed-special.toml")
    rebuilt_spec, rebuilt = ModelRecipe.load(path).build(dataset=dataset)
    df = api.apply_transforms(dataset.df, spec.transforms)
    for model in (glm, rebuilt):
        model.fit_reml(df[["x"]], df.claim_count, offset=df.log_exposure)
    before = [(type(level), repr(level)) for level in glm.relativities()["x"].level]
    after = [(type(level), repr(level)) for level in rebuilt.relativities()["x"].level]
    assert before == after
    assert before[-1] == (float, "9.0")
    np.testing.assert_allclose(
        glm.predict(df[["x"]], offset=df.log_exposure),
        rebuilt.predict(df[["x"]], offset=df.log_exposure),
    )
    assert ModelRecipe.from_model(glm, spec=spec).sha256 == recipe.sha256
    assert ModelRecipe.from_model(rebuilt, spec=rebuilt_spec).sha256 == recipe.sha256
    fitted_path = ModelRecipe.from_model(glm, spec=spec).save(tmp_path / "fitted-special.toml")
    assert ModelRecipe.load(fitted_path).sha256 == recipe.sha256
