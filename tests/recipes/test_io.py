import pytest

from pricing_pipeline.modeling.recipes import ModelRecipe
from pricing_pipeline.modeling.recipes.schema import RecipeError


def test_safe_save_and_replace(grouped_model_case, tmp_path):
    _, spec, glm = grouped_model_case
    recipe = ModelRecipe.from_model(glm, spec=spec)
    target = recipe.save(tmp_path / "é model.toml")
    with pytest.raises(FileExistsError):
        recipe.save(target)
    recipe.save(target, replace=True)
    assert ModelRecipe.load(target).sha256 == recipe.sha256
    link = tmp_path / "link.toml"
    link.symlink_to(target)
    with pytest.raises(RecipeError, match="symlink"):
        recipe.save(link, replace=True)
    with pytest.raises(RecipeError, match="symlink"):
        ModelRecipe.load(link)


def test_corrupt_toml(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text("not [valid")
    with pytest.raises(RecipeError, match="TOML"):
        ModelRecipe.load(path)


def test_null_markers_do_not_consume_user_mappings(grouped_model_case, tmp_path):
    from dataclasses import replace

    from superglm import Numeric, SuperGLM

    _dataset, spec, _ = grouped_model_case
    spec = replace(spec, features=["none"])
    recipe = ModelRecipe.from_model(
        SuperGLM(features={"none": Numeric()}, n_bins={"none": 1}), spec=spec
    )
    path = recipe.save(tmp_path / "none.toml")
    loaded = ModelRecipe.load(path)
    assert loaded.document.estimator["n_bins"]["none"] == 1
    assert loaded.sha256 == recipe.sha256


def test_interrupted_replace_leaves_previous_file(grouped_model_case, tmp_path, monkeypatch):
    from pricing_pipeline.modeling.recipes import io

    _, spec, glm = grouped_model_case
    recipe = ModelRecipe.from_model(glm, spec=spec)
    path = recipe.save(tmp_path / "model.toml")
    before = path.read_bytes()

    def fail(*args):
        raise OSError("interrupted")

    monkeypatch.setattr(io.os, "replace", fail)
    with pytest.raises(OSError, match="interrupted"):
        recipe.save(path, replace=True)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp"))


def test_exported_toml_supports_single_feature_and_transform_edits(grouped_model_case, tmp_path):
    import tomllib

    dataset, spec, glm = grouped_model_case
    recipe = ModelRecipe.from_model(glm, spec=spec)
    path = recipe.save(tmp_path / "editable.toml")
    content = path.read_text()
    payload = tomllib.loads(content)
    assert "feature_order" not in payload and "transform_order" not in payload
    assert "offset_source_column" not in payload and "offset_label" not in payload
    assert tuple(payload["features"]) == spec.features
    path.write_text(content + '\n[features.vehicle_age]\ntype = "Numeric"\n')
    appended = ModelRecipe.load(path)
    assert appended.document.feature_order == (*spec.features, "vehicle_age")
    path.write_text(content.replace('source = "exposure"', 'source = "earned_exposure"'))
    edited = ModelRecipe.load(path)
    rebuilt_spec, _ = edited.build(dataset=dataset)
    assert rebuilt_spec.offset_source_column == "earned_exposure"
    assert rebuilt_spec.offset_label == "log(earned_exposure)"
    assert rebuilt_spec.export_weight_column == "exposure"  # Its independent role stays explicit.


def test_export_orders_tables_and_keeps_explicit_nontransform_offsets(grouped_model_case, tmp_path):
    import tomllib
    from dataclasses import replace

    _, spec, glm = grouped_model_case
    recipe = ModelRecipe.from_model(
        glm,
        spec=replace(
            spec,
            transforms={},
            offset_column="already_logged",
            offset_source_column="exposure",
            offset_label="log(exposure)",
        ),
    )
    data = recipe.document.to_dict()
    data["feature_order"] = list(reversed(data["feature_order"]))
    from pricing_pipeline.modeling.recipes import RecipeDocument

    reordered = ModelRecipe(RecipeDocument(**data))
    path = reordered.save(tmp_path / "ordered.toml")
    payload = tomllib.loads(path.read_text())
    assert tuple(payload["features"]) == tuple(data["feature_order"])
    assert payload["offset_source_column"] == "exposure"
    assert payload["offset_label"] == "log(exposure)"
    assert ModelRecipe.load(path).sha256 == reordered.sha256


def test_old_explicit_order_documents_remain_readable(grouped_model_case, tmp_path):
    import tomli_w

    from pricing_pipeline.modeling.recipes.io import _nulls

    _, spec, glm = grouped_model_case
    recipe = ModelRecipe.from_model(glm, spec=spec)
    payload = recipe.document.to_dict()
    payload["features"] = dict(reversed(list(payload["features"].items())))
    path = tmp_path / "old.toml"
    path.write_text(tomli_w.dumps(_nulls(payload, encode=True)))
    assert ModelRecipe.load(path).sha256 == recipe.sha256
