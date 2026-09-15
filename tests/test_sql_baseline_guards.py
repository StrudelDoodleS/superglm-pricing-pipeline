"""Execute the SQL Server baseline guard predicates with SQLite NULL semantics.

Installation and THROW remain covered by SQL Server integration environments.
"""

import re
import sqlite3

import pytest

from pricing_pipeline.resources import migration_root


def _guard_query(name):
    sql = migration_root().joinpath("V049__sql_monitoring_baselines.sql").read_text()
    body = sql.split(f"CREATE OR ALTER TRIGGER pricing.{name}", 1)[1].split("\nGO", 1)[0]
    return re.search(r"IF EXISTS \((.*?)\)\s*THROW", body, re.DOTALL)[1]


@pytest.mark.parametrize(
    "identity, rejected",
    [
        ((10, 1, 2, "SUCCESS", 1, "PUBLISHED"), False),
        ((10, None, 2, "SUCCESS", 1, "PUBLISHED"), True),
        ((10, 1, None, "SUCCESS", 1, "PUBLISHED"), True),
        ((10, 1, 2, "FAILED", 1, "PUBLISHED"), True),
        ((10, 1, 2, "SUCCESS", 2, "PUBLISHED"), True),
        ((10, 1, 2, "SUCCESS", 1, "LOCAL_AUDIT"), True),
    ],
)
def test_sqlserver_baseline_insert_requires_successful_matching_published_package(
    identity, rejected
):
    query = _guard_query("TR_MODEL_MONITORING_BASELINE_LINEAGE_GUARD")
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            ATTACH ':memory:' AS pricing;
            CREATE TABLE pricing.MODEL_RUN (model_run_id, model_id, rate_package_id, run_status);
            CREATE TABLE pricing.PRICING_RATE_PACKAGE (rate_package_id, model_id, package_status);
            CREATE TABLE inserted (model_run_id, model_id, rate_package_id);
            INSERT INTO inserted VALUES (10, 1, 2);
        """)
        connection.execute("INSERT INTO pricing.MODEL_RUN VALUES (?,?,?,?)", identity[:4])
        connection.execute("INSERT INTO pricing.PRICING_RATE_PACKAGE VALUES (2,?,?)", identity[4:])
        assert bool(connection.execute(query).fetchall()) is rejected


@pytest.mark.parametrize(
    "changed, rejected",
    [
        ({}, False),
        ({"model_id": None}, True),
        ({"rate_package_id": None}, True),
        ({"run_status": "FAILED"}, True),
        ({"publication_receipt_sha256": "changed"}, True),
        ({"candidate_artifact_sha256": "changed"}, True),
        ({"model_source_sha256": "changed"}, True),
        (None, True),
    ],
)
def test_sqlserver_baseline_guard_preserves_source_identity_on_multirow_updates(changed, rejected):
    query = _guard_query("TR_MODEL_RUN_BASELINE_IDENTITY")
    source = {
        "model_run_id": 10,
        "model_id": 1,
        "rate_package_id": 2,
        "run_status": "SUCCESS",
        "model_version": "v1",
        "model_kind": "RAW",
        "export_id": "export",
        "manifest_id": "data",
        "publication_receipt_sha256": "a" * 64,
        "model_source_sha256": "b" * 64,
        "model_equivalence_sha256": "c" * 64,
        "candidate_artifact_sha256": "d" * 64,
        "candidate_artifact_format": "format",
        "candidate_artifact_size_bytes": 10,
        "candidate_python_version": "3.14",
        "candidate_superglm_version": "0.26",
        "rating_workbook_sha256": "e" * 64,
    }
    with sqlite3.connect(":memory:") as connection:
        connection.create_collation("Latin1_General_100_BIN2", lambda a, b: (a > b) - (a < b))
        connection.executescript("""
            ATTACH ':memory:' AS pricing;
            CREATE TABLE pricing.MODEL_MONITORING_BASELINE (model_run_id);
            INSERT INTO pricing.MODEL_MONITORING_BASELINE VALUES (10);
        """)
        for table in ("deleted", "inserted"):
            connection.execute(f"CREATE TABLE {table} ({','.join(source)})")
        placeholders = ",".join("?" for _ in source)
        connection.execute(f"INSERT INTO deleted VALUES ({placeholders})", tuple(source.values()))
        if changed is not None:
            connection.execute(
                f"INSERT INTO inserted VALUES ({placeholders})", tuple((source | changed).values())
            )
        # An unrelated run may change in the same statement.
        connection.execute(
            f"INSERT INTO deleted VALUES ({placeholders})",
            tuple((source | {"model_run_id": 11}).values()),
        )
        connection.execute(
            f"INSERT INTO inserted VALUES ({placeholders})",
            tuple((source | {"model_run_id": 11, "model_id": None}).values()),
        )
        assert bool(connection.execute(query).fetchall()) is rejected
