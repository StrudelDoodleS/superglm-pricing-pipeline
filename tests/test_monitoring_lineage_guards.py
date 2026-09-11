"""Exercise SQL Server guard predicates with SQL NULL semantics in SQLite.

The relational SELECT is portable; trigger installation/THROW still need a
SQL Server integration check.
"""

import re
import sqlite3

import pytest

from pricing_pipeline.resources import migration_root


def _latest_guard_query(trigger_name):
    query = None
    for migration in sorted(migration_root().glob("V*.sql"), reverse=True):
        sql = migration.read_text(encoding="utf-8")
        match = re.search(
            rf"CREATE OR ALTER TRIGGER {re.escape(trigger_name)}\b(.*?)(?:\nGO|\Z)",
            sql,
            re.DOTALL,
        )
        if match:
            predicate = re.search(r"IF EXISTS \((.*?)\)\s*BEGIN", match[1], re.DOTALL)
            assert predicate is not None
            query = predicate[1]
            break
    assert query is not None
    return query


@pytest.mark.parametrize(
    ("model_id", "package_id", "status", "rejected"),
    [
        (1, 2, "SUCCESS", False),
        (None, 2, "SUCCESS", True),
        (1, None, "SUCCESS", True),
        (None, None, "SUCCESS", True),
        (1, 2, "FAILED", True),
        (3, 2, "SUCCESS", True),
        (1, 3, "SUCCESS", True),
    ],
)
def test_sqlserver_fit_contract_guard_rejects_incomplete_baseline(
    model_id, package_id, status, rejected
):
    query = _latest_guard_query("mlops.TR_MODEL_FIT_CONTRACT_LINEAGE_GUARD")
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            ATTACH ':memory:' AS pricing;
            CREATE TABLE pricing.MODEL_RUN (
                model_run_id INTEGER, model_id INTEGER,
                rate_package_id INTEGER, run_status TEXT
            );
            CREATE TABLE pricing.PRICING_RATE_PACKAGE (
                rate_package_id INTEGER, model_id INTEGER, package_status TEXT
            );
            CREATE TABLE inserted (
                baseline_model_run_id INTEGER, model_id INTEGER, rate_package_id INTEGER
            );
            INSERT INTO pricing.PRICING_RATE_PACKAGE VALUES (2, 1, 'PUBLISHED');
            INSERT INTO inserted VALUES (10, 1, 2);
        """)
        connection.execute(
            "INSERT INTO pricing.MODEL_RUN VALUES (10, ?, ?, ?)",
            (model_id, package_id, status),
        )
        assert bool(connection.execute(query).fetchall()) is rejected


@pytest.mark.parametrize(
    ("new_identity", "rejected"),
    [
        ((10, 1, 2, "SUCCESS"), False),
        ((10, None, 2, "SUCCESS"), True),
        ((10, 1, None, "SUCCESS"), True),
        ((10, 1, 2, "FAILED"), True),
        ((10, 3, 2, "SUCCESS"), True),
        ((10, 1, 3, "SUCCESS"), True),
        (None, True),
    ],
)
def test_sqlserver_baseline_guard_preserves_identity_for_multirow_writes(new_identity, rejected):
    query = _latest_guard_query("pricing.TR_MODEL_RUN_MONITORING_LINEAGE_GUARD")
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            ATTACH ':memory:' AS mlops;
            CREATE TABLE mlops.MODEL_FIT_CONTRACT (baseline_model_run_id INTEGER);
            CREATE TABLE deleted (
                model_run_id INTEGER, model_id INTEGER,
                rate_package_id INTEGER, run_status TEXT
            );
            CREATE TABLE inserted (
                model_run_id INTEGER, model_id INTEGER,
                rate_package_id INTEGER, run_status TEXT
            );
            INSERT INTO mlops.MODEL_FIT_CONTRACT VALUES (10);
            INSERT INTO deleted VALUES (10, 1, 2, 'SUCCESS'), (11, 1, 3, 'STARTED');
            -- An unreferenced run may complete in the same statement.
            INSERT INTO inserted VALUES (11, 1, 3, 'SUCCESS');
        """)
        if new_identity is not None:
            connection.execute("INSERT INTO inserted VALUES (?, ?, ?, ?)", new_identity)
        assert bool(connection.execute(query).fetchall()) is rejected


@pytest.mark.parametrize("table", ["TERM", "LAMBDA", "RELATIVITY", "METRIC"])
@pytest.mark.parametrize("sealed", [0, 1, None])
def test_sqlserver_child_insert_guard_checks_every_parent(table, sealed):
    query = _latest_guard_query(f"mlops.TR_MODEL_MONITOR_{table}_INSERT_GUARD")
    # Execute the actual predicate; locking and THROW require a live SQL Server.
    assert "WITH (UPDLOCK, HOLDLOCK)" in query
    query = query.replace("WITH (UPDLOCK, HOLDLOCK)", "")
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            ATTACH ':memory:' AS mlops;
            CREATE TABLE mlops.MODEL_MONITOR_RUN (
                monitor_run_id TEXT, evidence_sealed INTEGER
            );
            CREATE TABLE inserted (monitor_run_id TEXT);
            INSERT INTO mlops.MODEL_MONITOR_RUN VALUES ('open-run', 0);
            INSERT INTO inserted VALUES ('open-run'), ('other-run');
        """)
        if sealed is not None:
            connection.execute(
                "INSERT INTO mlops.MODEL_MONITOR_RUN VALUES ('other-run', ?)",
                (sealed,),
            )
        assert bool(connection.execute(query).fetchall()) is (sealed != 0)


@pytest.mark.parametrize("old_seal, new_seal", [(0, 1), (0, 0), (1, 0), (1, 1), (1, None)])
def test_sqlserver_parent_guard_only_allows_sealing(old_seal, new_seal):
    query = _latest_guard_query("mlops.TR_MODEL_MONITOR_RUN_IMMUTABLE")
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            CREATE TABLE deleted (monitor_run_id TEXT, evidence_sealed INTEGER);
            CREATE TABLE inserted (monitor_run_id TEXT, evidence_sealed INTEGER);
            INSERT INTO deleted VALUES ('valid', 0);
            INSERT INTO inserted VALUES ('valid', 1);
        """)
        connection.execute("INSERT INTO deleted VALUES ('other', ?)", (old_seal,))
        if new_seal is not None:
            connection.execute("INSERT INTO inserted VALUES ('other', ?)", (new_seal,))
        assert bool(connection.execute(query).fetchall()) is ((old_seal, new_seal) != (0, 1))


def test_sqlserver_seal_guard_compares_every_nonseal_column_as_stored():
    from pricing_pipeline.resources import offline_sqlite_root

    sql = migration_root().joinpath("V041__seal_monitoring_evidence.sql").read_text()
    body = re.search(
        r"CREATE OR ALTER TRIGGER mlops.TR_MODEL_MONITOR_RUN_IMMUTABLE\b(.*?)\nGO",
        sql,
        re.DOTALL,
    )[1]
    query = re.findall(r"IF EXISTS \((.*?)\)\s*BEGIN", body, re.DOTALL)[1]
    # SQLite BLOB comparison provides the byte equality of T-SQL VARBINARY.
    query = re.sub(r"CONVERT\(VARBINARY\(MAX\), (\w+)\)", r"CAST(\1 AS BLOB)", query)
    with sqlite3.connect(":memory:") as connection:
        connection.execute("ATTACH ':memory:' AS pricing")
        connection.executescript(offline_sqlite_root().joinpath("pricing.sql").read_text())
        columns = [
            row[1] for row in connection.execute("PRAGMA pricing.table_info('MODEL_MONITOR_RUN')")
        ]
        columns.remove("evidence_sealed")
        definitions = ", ".join(f"{column} TEXT" for column in columns)
        connection.execute(f"CREATE TABLE deleted ({definitions})")
        connection.execute(f"CREATE TABLE inserted ({definitions})")
        placeholders = ", ".join("?" for _ in columns)
        original = ["original"] * len(columns)
        connection.execute(f"INSERT INTO deleted VALUES ({placeholders})", original)
        connection.execute(f"INSERT INTO inserted VALUES ({placeholders})", original)
        assert not connection.execute(query).fetchall()
        for column in columns:
            for value in ("changed", "ORIGINAL", "original ", None):
                connection.execute(f"UPDATE inserted SET {column} = ?", (value,))
                assert connection.execute(query).fetchall(), (column, value)
                connection.execute(f"UPDATE inserted SET {column} = 'original'")
