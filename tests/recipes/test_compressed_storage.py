"""Exercise the SQL Server recipe writer with SQLite's gzip function stand-in.

Only lock hints and the NVARCHAR cast are translated. These tests cover the
writer and existing readers; live tests cover SQL Server's functions and DDL.
"""

import gzip
import hashlib
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from pricing_pipeline.modeling.recipes import ModelRecipe, RecipeDocument
from pricing_pipeline.publishing.recipes import resolve_recipe


@pytest.fixture
def compressed_connection():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS pricing")
        driver = connection.connection.driver_connection
        driver.create_function(
            "COMPRESS", 1, lambda value: gzip.compress(value.encode("utf-16le"), mtime=0)
        )
        driver.create_function(
            "RECIPE_JSON",
            1,
            lambda value: gzip.decompress(value).decode("utf-16le"),
            deterministic=True,
        )
        connection.exec_driver_sql("CREATE TABLE pricing.PRICING_MODEL(model_id INTEGER)")
        connection.exec_driver_sql("INSERT INTO pricing.PRICING_MODEL VALUES (1)")
        connection.exec_driver_sql("""CREATE TABLE pricing.MODEL_RECIPE (
            recipe_id INTEGER PRIMARY KEY,
            model_id INTEGER NOT NULL,
            recipe_revision INTEGER NOT NULL,
            recipe_sha256 TEXT NOT NULL,
            recipe_format_version INTEGER NOT NULL,
            recipe_gzip BLOB NOT NULL,
            recipe_json TEXT GENERATED ALWAYS AS (RECIPE_JSON(recipe_gzip)) VIRTUAL,
            created_by TEXT NOT NULL,
            UNIQUE (model_id, recipe_revision),
            UNIQUE (model_id, recipe_sha256)
        )""")

        class SqlServerConnection:
            dialect = SimpleNamespace(name="mssql")

            def get_execution_options(self):
                return connection.get_execution_options()

            def execute(self, statement, params=None):
                sql = str(statement).replace(" WITH (UPDLOCK, HOLDLOCK)", "")
                sql = sql.replace("NVARCHAR(MAX)", "TEXT")
                return connection.execute(text(sql), params or {})

        yield SqlServerConnection()
    engine.dispose()


@pytest.mark.parametrize("large", [False, True])
def test_compressed_recipe_restores_unicode_and_reuses_its_identity(
    compressed_connection, recipe_data, large
):
    labels = ["Łódź", "東京", "🙂"]
    if large:
        labels.extend(f"地域_{i}" for i in range(2000))
    recipe_data["features"]["region"]["groups"][1]["levels"].extend(labels)
    recipe = ModelRecipe(RecipeDocument(**recipe_data))
    canonical = recipe.canonical_json
    if large:
        assert len(canonical.encode("utf-16le")) > 8000
    connection = compressed_connection
    saved = resolve_recipe(connection, model_id=1, recipe=recipe, created_by="test")
    row = connection.execute(text("SELECT * FROM pricing.MODEL_RECIPE")).mappings().one()
    restored = gzip.decompress(row["recipe_gzip"]).decode("utf-16le")
    assert restored == row["recipe_json"] == canonical
    assert hashlib.sha256(restored.encode("utf-8")).hexdigest() == saved.recipe_sha256
    assert len(row["recipe_gzip"]) < len(canonical.encode("utf-16le"))
    assert resolve_recipe(connection, model_id=1, recipe=recipe, created_by="retry") == saved
    assert connection.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RECIPE")).scalar_one() == 1
