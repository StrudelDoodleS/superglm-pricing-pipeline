from sqlalchemy import text

from pricing_pipeline import notebook as api


def test_saved_recipe_visible_in_existing_views(fitted_case):
    pricing, model, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    with pricing.engine.connect() as c:
        for view in ("V_FINAL_MODEL_RELATIVITY", "V_MODEL_VALIDATION_SUMMARY"):
            rows = c.execute(
                text(f"SELECT recipe_revision,recipe_sha256,recipe_status FROM pricing.{view}")
            ).all()
            assert rows
            assert set(rows) == {(saved.recipe_revision, saved.recipe_sha256, "CAPTURED")}
        columns = c.execute(text("SELECT * FROM pricing.V_MODEL_MONITORING_RUN WHERE 1=0")).keys()
        assert {
            "baseline_recipe_revision",
            "baseline_recipe_sha256",
            "baseline_recipe_status",
        } <= set(columns)
    summary = api.list_model_versions(pricing, model=model)
    assert {"Recipe", "Recipe status"} <= set(summary.columns)
    technical = api.list_model_versions(pricing, model=model, technical=True)
    assert {"recipe_revision", "recipe_sha256", "recipe_status"} <= set(technical.columns)
