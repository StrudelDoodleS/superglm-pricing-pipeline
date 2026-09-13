"""Verify editor parent recipe evidence against SQL before inheriting it."""

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from pricing_pipeline import notebook as api
from pricing_pipeline.modeling.recipes import ModelRecipe
from pricing_pipeline.publishing.editor_parent import load_parent_candidate
from pricing_pipeline.publishing.recipes import resolve_recipe
from pricing_pipeline.workbench.submission import EditorSubmissionError


@pytest.fixture
def published_parent(fitted_case):
    pricing, model, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    # The offline fixture has no deployment. Mark its package published so the
    # editor loader exercises the same SQL/artifact boundary as a remote parent.
    with pricing.engine.begin() as connection:
        connection.execute(
            text("UPDATE pricing.PRICING_RATE_PACKAGE SET package_status='PUBLISHED'"),
        )
    build = candidate.completed_build
    submission = SimpleNamespace(
        model_name=model.spec.name,
        deployment_slot=model.spec.deployment_slot,
        source_package_version=saved.package_version,
        parent_rate_package_id=saved.rate_package_id,
        parent_model_run_id=saved.model_run_id,
        manifest_id=build.manifest_id,
        split_set_id=build.split_set_id,
        baseline_candidate_sha256=build.candidate_artifact_sha256,
        model_source_sha256=build.model_source_sha256,
    )
    return pricing, model, candidate, submission


def _load_parent(case):
    pricing, model, _, submission = case
    return load_parent_candidate(
        pricing.engine,
        submission,
        allowed_root=pricing.settings.workbench_artifact_root,
        model_config=model.config,
    )


def test_editor_parent_retains_verified_recipe(published_parent):
    parent = _load_parent(published_parent)
    assert parent.bundle.recipe_capture == published_parent[2].completed_build.recipe_capture


@pytest.mark.parametrize(
    "field,value",
    [
        ("recipe_json", "{}"),
        ("recipe_sha256", "a" * 64),
        ("recipe_format_version", 99),
    ],
)
def test_editor_parent_rejects_changed_sql_recipe(published_parent, field, value):
    pricing, _, _, _ = published_parent
    # Simulate damaged audit data while retaining the original, hash-valid bundle.
    with pricing.engine.begin() as connection:
        connection.execute(text("DROP TRIGGER pricing.TR_MODEL_RECIPE_UPDATE"))
        connection.exec_driver_sql("PRAGMA ignore_check_constraints = ON")
        try:
            connection.execute(
                text(f"UPDATE pricing.MODEL_RECIPE SET {field}=:value"), {"value": value}
            )
        finally:
            connection.exec_driver_sql("PRAGMA ignore_check_constraints = OFF")
    with pytest.raises(EditorSubmissionError, match="parent.*recipe"):
        _load_parent(published_parent)


@pytest.mark.parametrize("status", ["LEGACY", "UNSUPPORTED"])
def test_editor_parent_rejects_changed_sql_recipe_status(published_parent, status):
    pricing, _, _, _ = published_parent
    with pricing.engine.begin() as connection:
        connection.execute(text("DROP TRIGGER pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE"))
        connection.execute(
            text(
                "UPDATE pricing.MODEL_RUN SET recipe_status=:status, recipe_id=NULL, recipe_unavailable_reason=:reason"
            ),
            {"status": status, "reason": "custom splitter" if status == "UNSUPPORTED" else None},
        )
    with pytest.raises(EditorSubmissionError, match="parent.*recipe"):
        _load_parent(published_parent)


def test_editor_parent_rejects_a_different_valid_recipe_link(published_parent):
    pricing, model, candidate, _ = published_parent
    other = ModelRecipe(candidate.recipe.document.model_copy(update={"fit_mode": "fit"}))
    with pricing.engine.begin() as connection:
        stored = resolve_recipe(
            connection, model_id=model.model_id, recipe=other, created_by="test"
        )
        connection.execute(text("DROP TRIGGER pricing.TR_MODEL_RUN_RECIPE_IMMUTABLE"))
        connection.execute(
            text("UPDATE pricing.MODEL_RUN SET recipe_id=:recipe"), {"recipe": stored.recipe_id}
        )
    with pytest.raises(EditorSubmissionError, match="parent.*recipe"):
        _load_parent(published_parent)
