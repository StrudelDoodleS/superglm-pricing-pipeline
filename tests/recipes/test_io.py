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
