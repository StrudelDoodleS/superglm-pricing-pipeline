# Generated notebook code is intentionally executed to verify the analyst workflow.
# ruff: noqa: S102
import json

from pricing_pipeline import notebook as api
from pricing_pipeline.scaffold.config import ScaffoldOptions
from pricing_pipeline.scaffold.service import scaffold_pricing_model


def test_wildcard_notebook_import_can_capture_a_recipe(grouped_model_case):
    _, spec, glm = grouped_model_case
    namespace = {"spec": spec, "glm": glm}
    exec("from pricing_pipeline.notebook import *", namespace)
    exec("recipe = ModelRecipe.from_model(glm, spec=spec)", namespace)
    assert namespace["recipe"].sha256 == api.ModelRecipe.from_model(glm, spec=spec).sha256


def test_generated_configuration_authors_exports_and_loads(grouped_model_case, tmp_path):
    dataset, _, _ = grouped_model_case
    # Use the renderer's chosen feature/target names with a realistic fresh dataset.
    df = dataset.df.rename(columns={"claim_count": "target", "x": "feature_1"})
    df["segment"] = df["region"]
    dataset = api.PricingDataset(df, name="new_data", source="test", key="id", as_of="as_of")
    result = scaffold_pricing_model(
        ScaffoldOptions(
            model_name="RECIPE_TEST", model_label="Recipe test", target_name="target", root=tmp_path
        )
    )
    model_dir = tmp_path / "pricing_models" / result.package_name
    notebook = json.loads((model_dir / "03_model_training.ipynb").read_text())
    code = ["".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"]
    exports = [source for source in code if ".recipe.save(" in source]
    assert exports and all(source.startswith("#") for source in exports)
    config = next(source for source in code if "MODEL = PricingModelSpec(" in source)
    assert "if RECIPE_PATH is None:" in config
    import superglm

    from pricing_pipeline.models.config import ValidationSplitConfig

    namespace = dict(
        dataset=dataset,
        RECIPE_PATH=None,
        MODEL_DIR=model_dir,
        display=lambda x: None,
        **{name: getattr(superglm, name) for name in ["SuperGLM", "Numeric", "Categorical"]},
        **{
            name: getattr(api, name)
            for name in [
                "ModelRecipe",
                "PricingModelSpec",
                "apply_transforms",
                "Log",
                "Log1p",
                "Clip",
            ]
        },
        ValidationSplitConfig=ValidationSplitConfig,
    )
    exec(compile(config, "generated-model-config", "exec"), namespace)
    recipe = api.ModelRecipe.from_model(namespace["raw_superglm_model"], spec=namespace["MODEL"])
    path = recipe.save(model_dir / "model.toml")
    pricing = api.connect(mode="local", local_root=tmp_path / "audit")
    namespace.update(
        pricing=pricing,
        **{
            name: getattr(api, name)
            for name in ("register_model", "fit_model", "save_model_version")
        },
    )
    shared = [
        next(source for source in code if source.startswith(prefix))
        for prefix in (
            "model = register_model",
            "# Fit and validate.",
            "raw_published = save_model_version",
        )
    ]

    def fit_and_save():
        for source in shared:
            exec(compile(source, "generated-fit-save", "exec"), namespace)
        return namespace["raw_published"]

    original = fit_and_save()
    assert namespace["raw_candidate"].recipe.sha256 == recipe.sha256
    new_df = dataset.df.copy()
    new_df["as_of"] = "2026-09-02"
    fresh = api.PricingDataset(new_df, name="fresh_data", source="test", key="id", as_of="as_of")
    namespace.update(dataset=fresh, RECIPE_PATH=path)
    exec(compile(config, "generated-recipe-config", "exec"), namespace)
    assert namespace["MODEL"].dataset is fresh
    assert (
        api.ModelRecipe.from_model(namespace["raw_superglm_model"], spec=namespace["MODEL"]).sha256
        == recipe.sha256
    )
    refreshed = fit_and_save()
    assert refreshed.recipe_revision == original.recipe_revision == 1
    assert refreshed.model_run_id != original.model_run_id
    assert refreshed.manifest_id != original.manifest_id

    challenger_path = model_dir / "challenger.toml"
    challenger_path.write_text(path.read_text() + '\n[features.z]\ntype = "Numeric"\n')
    namespace["RECIPE_PATH"] = challenger_path
    exec(compile(config, "generated-challenger-config", "exec"), namespace)
    saved_challenger = fit_and_save()
    assert saved_challenger.recipe_revision == 2
    assert "z" in namespace["MODEL"].features

    for i, source in enumerate(code):
        compile(source, f"generated-cell-{i}", "exec")
    grouping = next(source for source in code if "LEVEL_GROUPINGS = (" in source)
    assert "RECIPE_PATH is None" in grouping
    stale_grouping = model_dir / "stale_groupings.joblib"
    stale_grouping.write_bytes(b"not a valid grouping artifact")
    namespace["GROUPING_ARTIFACT_PATH"] = stale_grouping
    exec(compile(grouping, "generated-grouping-branch", "exec"), namespace)
    assert namespace["LEVEL_GROUPINGS"] == {}
    with pricing.engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM pricing.PRICING_MODEL_DEPLOYMENT"
            ).scalar_one()
            == 0
        )
    pricing.engine.dispose()
