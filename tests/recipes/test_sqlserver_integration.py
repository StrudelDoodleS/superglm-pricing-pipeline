"""Live checks only for an explicitly supplied SQL Server test destination.

No database creation/reset. Committed test model history remains for inspection.
Start at V046 to exercise upgrade; V048 supports repeated allocation/publication checks.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from pricing_pipeline import notebook as api
from pricing_pipeline.infra.db import configure_engine
from pricing_pipeline.infra.migrations import apply_migrations
from pricing_pipeline.infra.runtime import runtime_from_module
from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.recipes import ModelRecipe
from pricing_pipeline.publishing.recipes import resolve_recipe

RUNTIME = os.environ.get("PRICING_RECIPE_TEST_RUNTIME")
DATABASE = os.environ.get("PRICING_RECIPE_TEST_DATABASE")
pytestmark = pytest.mark.skipif(
    not (RUNTIME and DATABASE),
    reason="live SQL Server recipe tests require explicit PRICING_RECIPE_TEST_RUNTIME and PRICING_RECIPE_TEST_DATABASE",
)


@pytest.fixture(scope="module")
def live_engine():
    runtime = runtime_from_module(RUNTIME)
    engine = configure_engine(runtime.get_engine(), runtime.settings.schema_names)
    assert engine.dialect.name == "mssql"
    with engine.connect() as c:
        assert c.execute(text("SELECT DB_NAME()")).scalar_one().casefold() == DATABASE.casefold(), (
            "test database mismatch; no writes performed"
        )
        last = c.execute(text("SELECT MAX(version_file) FROM dbo.SCHEMA_MIGRATION")).scalar_one()
    assert last and last.startswith(("V046__", "V048__")), (
        "provide a designated test database at V046 or V048; no automatic reset"
    )
    yield engine, runtime, last
    engine.dispose()


def test_live_upgrade_preserves_historical_runs(live_engine):
    engine, _, last = live_engine
    if not last.startswith("V046__"):
        pytest.skip("destination already upgraded; V046-to-V048 upgrade not exercised")
    schema = schema_names_from_connectable(engine).pricing
    query = text(
        f"SELECT model_run_id,model_id,model_version,manifest_id,rate_package_id,completed_ts FROM {schema}.MODEL_RUN ORDER BY model_run_id"
    )
    with engine.connect() as c:
        before = c.execute(query).all()
    applied = apply_migrations(engine)
    assert applied == ["V047__model_recipes.sql", "V048__recipe_revision_views.sql"]
    with engine.connect() as c:
        assert c.execute(query).all() == before
        assert (
            c.execute(
                text(
                    f"SELECT COUNT(*) FROM {schema}.MODEL_RUN WHERE recipe_id IS NOT NULL OR recipe_status <> 'LEGACY'"
                )
            ).scalar_one()
            == 0
        )


@pytest.fixture
def live_candidate(live_engine, grouped_model_case, tmp_path):
    engine, runtime, _ = live_engine
    # Safe when tests are selected individually; existing migrations are no-ops.
    apply_migrations(engine)
    dataset, spec, glm = grouped_model_case
    spec = replace(spec, name="RECIPE_TEST_" + uuid4().hex[:16].upper())
    source = tmp_path / "definition.py"
    source.write_text("# live recipe test\n")
    settings = replace(
        runtime.settings,
        workbench_artifact_root=tmp_path / "artifacts",
        validation_split_artifact_root=tmp_path / "splits",
    )
    context = api.NotebookContext(
        engine=engine,
        settings=settings,
        mode="remote",
        write_allowed=True,
        destination=f"live test: {DATABASE}",
    )
    model = api.register_model(context, spec, source_root=tmp_path)
    candidate = api.fit_model(
        context,
        model=model,
        frame=api.apply_transforms(dataset.df, spec.transforms),
        superglm_model=glm,
    )
    return context, model, candidate


def test_live_concurrent_save_and_views(live_candidate):
    context, _, candidate = live_candidate
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: api.save_model_version(context, candidate), range(2)))
    assert results[0].model_run_id == results[1].model_run_id
    assert results[0].recipe_revision == results[1].recipe_revision == 1
    schema = schema_names_from_connectable(context.engine).pricing
    with context.engine.connect() as c:
        for view in ("V_FINAL_MODEL_RELATIVITY", "V_MODEL_VALIDATION_SUMMARY"):
            rows = c.execute(
                text(
                    f"SELECT recipe_revision,recipe_sha256,recipe_status FROM {schema}.{view} WHERE model_run_id=:run"
                ),
                {"run": results[0].model_run_id},
            ).all()
            assert rows and set(rows) == {(1, candidate.recipe.sha256, "CAPTURED")}
    with pytest.raises(DBAPIError), context.engine.begin() as c:
        c.execute(
            text(
                f"UPDATE {schema}.MODEL_RUN SET recipe_id=NULL,recipe_status='LEGACY' WHERE model_run_id=:run"
            ),
            {"run": results[0].model_run_id},
        )


def test_live_concurrent_different_recipes_and_rollback(live_candidate):
    context, model, candidate = live_candidate
    original = candidate.recipe
    changed = ModelRecipe(original.document.model_copy(update={"fit_mode": "fit"}))

    def allocate(recipe):
        with context.engine.begin() as c:
            return resolve_recipe(c, model_id=model.model_id, recipe=recipe, created_by="live-test")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(allocate, [original, changed]))
    assert {r.recipe_revision for r in results} == {1, 2}
    rollback_recipe = ModelRecipe(original.document.model_copy(update={"scoring": ["deviance"]}))
    with pytest.raises(RuntimeError, match="abort"), context.engine.begin() as c:
        resolve_recipe(c, model_id=model.model_id, recipe=rollback_recipe, created_by="live-test")
        raise RuntimeError("abort")
    schema = schema_names_from_connectable(context.engine).pricing
    with context.engine.connect() as c:
        assert (
            c.execute(
                text(f"SELECT COUNT(*) FROM {schema}.MODEL_RECIPE WHERE model_id=:model"),
                {"model": model.model_id},
            ).scalar_one()
            == 2
        )
