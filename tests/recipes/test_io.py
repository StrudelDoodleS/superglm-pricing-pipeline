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
