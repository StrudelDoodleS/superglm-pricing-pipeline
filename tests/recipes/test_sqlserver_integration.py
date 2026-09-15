"""Live checks only for an explicitly supplied SQL Server test destination.

No database creation/reset. Committed test model history remains for inspection.
Accepts designated databases from V046 through V052. The compression upgrade
test also creates an isolated schema and rolls back all of its changes.
"""

import gzip
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from pricing_pipeline import notebook as api
from pricing_pipeline.infra.db import configure_engine
from pricing_pipeline.infra.migrations import (
    _execute_migration_batch,
    apply_migrations,
    migration_files,
    render_migration_sql,
    split_sql_server_batches,
)
from pricing_pipeline.infra.runtime import runtime_from_module
from pricing_pipeline.infra.schema import SchemaNames, schema_names_from_connectable
from pricing_pipeline.modeling.recipes import ModelRecipe, RecipeDocument
from pricing_pipeline.publishing.recipes import resolve_recipe
from pricing_pipeline.resources import migration_root

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
    assert last and any(last.startswith(f"V{number:03}__") for number in range(46, 53)), (
        "provide a designated test database at V046 through V052; no automatic reset"
    )
    yield engine, runtime, last
    engine.dispose()


def test_live_upgrade_preserves_historical_runs(live_engine):
    engine, _, last = live_engine
    if not last.startswith("V046__"):
        pytest.skip("destination already upgraded; V046 upgrade not exercised")
    schema = schema_names_from_connectable(engine).pricing
    query = text(
        f"SELECT model_run_id,model_id,model_version,manifest_id,rate_package_id,completed_ts FROM {schema}.MODEL_RUN ORDER BY model_run_id"
    )
    with engine.connect() as c:
        before = c.execute(query).all()
    applied = apply_migrations(engine)
    assert applied == [path.name for path in migration_files() if path.name > last]
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
    params = {"run": results[0].model_run_id}
    with pytest.raises(DBAPIError), context.engine.begin() as c:
        c.execute(
            text(
                f"UPDATE {schema}.MODEL_RUN SET run_status='FAILED',rate_package_id=NULL WHERE model_run_id=:run"
            ),
            params,
        )
    try:
        for assignment in (
            "recipe_id=NULL,recipe_status='LEGACY'",
            "model_id=NULL",
            "recipe_unavailable_reason='changed'",
        ):
            with pytest.raises(DBAPIError), context.engine.begin() as c:
                c.execute(
                    text(f"UPDATE {schema}.MODEL_RUN SET {assignment} WHERE model_run_id=:run"),
                    params,
                )
        with context.engine.begin() as c:
            c.execute(
                text(
                    f"UPDATE {schema}.MODEL_RUN SET recipe_unavailable_reason=NULL, model_id=model_id WHERE model_run_id=:run"
                ),
                params,
            )
    finally:
        with context.engine.begin() as c:
            c.execute(
                text(
                    f"UPDATE {schema}.MODEL_RUN SET run_status='SUCCESS',rate_package_id=:package WHERE model_run_id=:run"
                ),
                params | {"package": results[0].rate_package_id},
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


def test_live_compression_upgrade_preserves_existing_recipe_and_links(live_engine, recipe_data):
    engine, _, _ = live_engine
    schema = "recipe_gzip_test_" + uuid4().hex[:12]
    schemas = SchemaNames(pricing=schema)
    recipe_data["features"]["region"]["groups"][1]["levels"].extend(
        ["Łódź", "東京", "🙂", *(f"地域_{i}" for i in range(2000))]
    )
    recipe = ModelRecipe(RecipeDocument(**recipe_data))
    original = recipe.canonical_json
    assert len(original.encode("utf-16le")) > 8000
    old_batches = split_sql_server_batches(
        render_migration_sql(
            migration_root().joinpath("V047__model_recipes.sql").read_text(), schemas
        )
    )
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(f"CREATE SCHEMA {schema}")
            connection.exec_driver_sql(
                f"CREATE TABLE {schema}.PRICING_MODEL(model_id BIGINT PRIMARY KEY)"
            )
            connection.exec_driver_sql(f"INSERT INTO {schema}.PRICING_MODEL VALUES (1)")
            _execute_migration_batch(connection, old_batches[0])
            _execute_migration_batch(
                connection,
                next(batch for batch in old_batches if "TR_MODEL_RECIPE_IMMUTABLE\n" in batch),
            )
            connection.exec_driver_sql(
                f"EXEC sys.sp_addextendedproperty @name=N'MS_Description', @value=N'Original recipe', "
                f"@level0type=N'SCHEMA', @level0name=N'{schema}', "
                "@level1type=N'TABLE', @level1name=N'MODEL_RECIPE'"
            )
            connection.execute(
                text(f"""INSERT INTO {schema}.MODEL_RECIPE
                    (model_id,recipe_revision,recipe_sha256,recipe_format_version,recipe_json,created_by)
                    VALUES (1,7,:sha,1,:json,'compression-test')"""),
                {"sha": recipe.sha256, "json": original},
            )
            connection.exec_driver_sql(f"""CREATE TABLE {schema}.RECIPE_LINK (
                recipe_id BIGINT NOT NULL REFERENCES {schema}.MODEL_RECIPE(recipe_id)
            )""")
            connection.exec_driver_sql(f"INSERT INTO {schema}.RECIPE_LINK VALUES (1)")
            columns = (
                "recipe_id,model_id,recipe_revision,recipe_sha256,recipe_format_version,"
                "recipe_json,created_ts,created_by"
            )
            before = connection.execute(text(f"SELECT {columns} FROM {schema}.MODEL_RECIPE")).one()
            migration = migration_root().joinpath("V052__compressed_model_recipes.sql").read_text()
            for batch in split_sql_server_batches(render_migration_sql(migration, schemas)):
                _execute_migration_batch(connection, batch)
            after = connection.execute(text(f"SELECT {columns} FROM {schema}.MODEL_RECIPE")).one()
            assert after == before
            packed = connection.execute(
                text(f"SELECT recipe_gzip FROM {schema}.MODEL_RECIPE")
            ).scalar_one()
            restored = gzip.decompress(packed).decode("utf-16le")
            assert restored == original
            assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == recipe.sha256
            assert (
                connection.execute(
                    text("SELECT CAST(DECOMPRESS(:payload) AS NVARCHAR(MAX))"),
                    {"payload": gzip.compress(original.encode("utf-16le"), mtime=0)},
                ).scalar_one()
                == original
            )
            assert (
                connection.execute(text(f"SELECT recipe_id FROM {schema}.RECIPE_LINK")).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text(
                        "SELECT is_persisted FROM sys.computed_columns WHERE object_id=OBJECT_ID(:table) AND name='recipe_json'"
                    ),
                    {"table": f"{schema}.MODEL_RECIPE"},
                ).scalar_one()
                is False
            )
            assert (
                connection.execute(
                    text(
                        "SELECT is_disabled FROM sys.triggers WHERE object_id=OBJECT_ID(:trigger)"
                    ),
                    {"trigger": f"{schema}.TR_MODEL_RECIPE_IMMUTABLE"},
                ).scalar_one()
                is False
            )
            with pytest.raises(DBAPIError, match="immutable"):
                connection.exec_driver_sql(
                    f"UPDATE {schema}.MODEL_RECIPE SET recipe_gzip=recipe_gzip"
                )
        finally:
            transaction.rollback()
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT SCHEMA_ID(:schema)"), {"schema": schema}).scalar_one()
            is None
        )


def test_live_compressed_publication_is_readable_in_python_and_sql(live_candidate):
    context, _, candidate = live_candidate
    saved = api.save_model_version(context, candidate)
    schema = schema_names_from_connectable(context.engine).pricing
    with context.engine.connect() as connection:
        row = (
            connection.execute(
                text(f"""SELECT recipe.recipe_gzip, recipe.recipe_json, recipe.recipe_sha256
                FROM {schema}.MODEL_RECIPE recipe JOIN {schema}.MODEL_RUN run
                  ON run.recipe_id=recipe.recipe_id WHERE run.model_run_id=:run"""),
                {"run": saved.model_run_id},
            )
            .mappings()
            .one()
        )
    restored = gzip.decompress(row["recipe_gzip"]).decode("utf-16le")
    assert restored == row["recipe_json"] == candidate.recipe.canonical_json
    assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == row["recipe_sha256"]
    assert api.save_model_version(context, candidate).recipe_revision == saved.recipe_revision


@pytest.mark.parametrize(
    "payload",
    [b"not gzip", gzip.compress(b""), gzip.compress("[]".encode("utf-16le"))],
    ids=["invalid-gzip", "empty-json", "json-array"],
)
def test_live_recipe_rejects_invalid_compressed_content(live_candidate, payload):
    context, model, _ = live_candidate
    schema = schema_names_from_connectable(context.engine).pricing
    with pytest.raises(DBAPIError), context.engine.begin() as connection:
        connection.execute(
            text(f"""INSERT INTO {schema}.MODEL_RECIPE
                (model_id,recipe_revision,recipe_sha256,recipe_format_version,recipe_gzip,created_by)
                VALUES (:model,1,:sha,1,:payload,'compression-test')"""),
            {"model": model.model_id, "sha": "a" * 64, "payload": payload},
        )
