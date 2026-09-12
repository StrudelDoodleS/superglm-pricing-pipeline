from pricing_pipeline.modeling.recipes.schema import RecipeDocument


def test_bindings_and_execution_do_not_change_identity(recipe_data):
    doc = RecipeDocument(**recipe_data)
    changed = doc.model_copy(
        update={
            "label": "New",
            "name": "OTHER",
            "deployment_slot": "TEST",
            "estimator": dict(doc.estimator) | {"retain_fit_state": True},
        }
    )
    assert changed.sha256 == doc.sha256
    assert changed.to_dict() != doc.to_dict()


def test_feature_order_is_semantic(recipe_data):
    doc = RecipeDocument(**recipe_data)
    assert (
        doc.model_copy(update={"feature_order": tuple(reversed(doc.feature_order))}).sha256
        != doc.sha256
    )


def test_semantic_changes_are_exact(recipe_data):
    doc = RecipeDocument(**recipe_data)
    for change in [
        {"fit_mode": "fit"},
        {"sample_weight_column": "weight"},
        {"estimator": dict(doc.estimator) | {"tol": 1.00000000001e-6}},
        {"scoring": ["deviance"]},
    ]:
        assert doc.model_copy(update=change).sha256 != doc.sha256


def test_mapping_order_is_irrelevant(recipe_data):
    doc = RecipeDocument(**recipe_data)
    data = doc.to_dict()
    data["estimator"] = dict(reversed(list(data["estimator"].items())))
    assert RecipeDocument(**data).canonical_json == doc.canonical_json
