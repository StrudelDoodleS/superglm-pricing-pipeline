"""Exercise deferred DBAPI batch results against a real transactional SQLite database.

The cursor adapter models nextset-driven execution. SQL Server integration is
still needed to verify server-specific DDL and extended properties.
"""

import os
import sqlite3
from collections import deque
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from pricing_pipeline.infra import migrations


class DeferredCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.pending = deque()

    def execute(self, statement, parameters=()):
        if statement.startswith("/* deferred */"):
            self.pending = deque(part.strip() for part in statement.split(";") if part.strip())
            return self.cursor.execute(self.pending.popleft(), parameters)
        return self.cursor.execute(statement, parameters)

    def nextset(self):
        if not self.pending:
            return None
        self.cursor.execute(self.pending.popleft())
        return True

    def close(self):
        self.pending.clear()
        self.cursor.close()

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class DeferredConnection:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")

    def cursor(self):
        return DeferredCursor(self.db.cursor())

    def __getattr__(self, name):
        return getattr(self.db, name)


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", creator=DeferredConnection)
    with engine.begin() as con:
        con.exec_driver_sql("CREATE TABLE descriptions (name TEXT PRIMARY KEY)")
    yield engine
    engine.dispose()


def test_migration_batch_finishes_after_row_counts_and_select_results(engine):
    with engine.begin() as con:
        migrations._execute_migration_batch(
            con,
            "/* deferred */ INSERT INTO descriptions VALUES ('table');"
            " SELECT 1; INSERT INTO descriptions VALUES ('view')",
        )
    with engine.connect() as con:
        assert con.execute(text("SELECT name FROM descriptions ORDER BY name")).scalars().all() == [
            "table",
            "view",
        ]


@pytest.mark.parametrize("first", ["INSERT INTO descriptions VALUES ('table'); SELECT 1;", ""])
def test_migration_batch_propagates_errors_and_rolls_back(engine, first):
    with pytest.raises(sqlite3.OperationalError, match="no such table"), engine.begin() as con:
        migrations._execute_migration_batch(
            con, "/* deferred */ " + first + "INSERT INTO missing_table VALUES (1)"
        )
    with engine.connect() as con:
        assert con.exec_driver_sql("SELECT COUNT(*) FROM descriptions").scalar_one() == 0
        assert con.exec_driver_sql("SELECT 1").scalar_one() == 1


def test_migration_error_names_file_and_batch_without_recording_success(tmp_path, monkeypatch):
    path = tmp_path / "V039__example.sql"
    path.write_text("SELECT 1;\nGO\nSELECT 2;\n")
    monkeypatch.setattr(migrations, "_ensure_schema_migration_table", lambda con: None)
    monkeypatch.setattr(migrations, "_ensure_schema_configuration", lambda con, schemas: None)
    failure = RuntimeError("missing description")

    def execute(con, batch):
        if batch == "SELECT 2;":
            raise failure

    monkeypatch.setattr(migrations, "_execute_migration_batch", execute, raising=False)
    recorded = []

    class Connection:
        def execute(self, statement, parameters=None):
            if "INSERT INTO dbo.SCHEMA_MIGRATION" in str(statement):
                recorded.append(parameters)
            return SimpleNamespace(mappings=lambda: SimpleNamespace(one_or_none=lambda: None))

    with pytest.raises(RuntimeError, match="missing description") as caught:
        migrations.apply_migrations_in_transaction(Connection(), tmp_path, acquire_lock=False)
    assert caught.value is failure
    assert "V039__example.sql" in " ".join(caught.value.__notes__)
    assert "batch 2 of 2" in " ".join(caught.value.__notes__)
    assert recorded == []


@pytest.mark.skipif(
    not (
        os.environ.get("PRICING_RECIPE_TEST_RUNTIME")
        and os.environ.get("PRICING_RECIPE_TEST_DATABASE")
    ),
    reason="live batch test requires an explicit SQL Server test runtime and database",
)
def test_live_batch_executes_after_many_results_and_surfaces_late_error():
    from pricing_pipeline.infra.runtime import runtime_from_module

    runtime = runtime_from_module(os.environ["PRICING_RECIPE_TEST_RUNTIME"])
    engine = runtime.get_engine()
    try:
        with engine.connect() as con:
            assert (
                con.execute(text("SELECT DB_NAME()")).scalar_one().casefold()
                == os.environ["PRICING_RECIPE_TEST_DATABASE"].casefold()
            )
            # Only connection-local temporary objects; rollback removes all test DDL.
            migrations._execute_migration_batch(
                con, "CREATE TABLE #batch_completion (value int NOT NULL)"
            )
            results = "SELECT REPLICATE(N'x', 4000);\n" * 100
            migrations._execute_migration_batch(
                con, results + "INSERT INTO #batch_completion VALUES (1);"
            )
            assert con.exec_driver_sql("SELECT COUNT(*) FROM #batch_completion").scalar_one() == 1
            with pytest.raises(engine.dialect.loaded_dbapi.Error, match="batch completion test"):
                migrations._execute_migration_batch(
                    con, results + "THROW 51099, 'batch completion test', 1;"
                )
            con.rollback()
    finally:
        engine.dispose()
