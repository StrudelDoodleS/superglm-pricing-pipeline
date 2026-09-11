"""Exercise the pointer retirement predicate without requiring SQL Server.

The relational guard runs in SQLite after removing SQL Server lock hints.
DDL execution, locking, and dependency checks still require SQL Server.
"""

import re
import sqlite3

import pytest

from pricing_pipeline.resources import migration_root


@pytest.mark.parametrize(
    ("pointers", "deployments", "rejected"),
    [
        ([], [], False),
        ([(1, "PROD", 10)], [(1, "PROD", 10, None)], False),
        ([(1, "PROD", 10)], [], True),
        ([(1, "PROD", 10)], [(1, "PROD", 11, None)], True),
        ([(1, "PROD", 10)], [(1, "UAT", 10, None)], True),
        ([(1, "PROD", 10)], [(2, "PROD", 10, None)], True),
        ([(1, "PROD", 10)], [(1, "PROD", 10, "2026-09-10")], True),
        (
            [(1, "PROD", 10), (1, "UAT", 11)],
            [(1, "PROD", 10, None), (1, "UAT", 11, None)],
            False,
        ),
        (
            [(1, "PROD", 10), (1, "UAT", 11)],
            [(1, "PROD", 10, None), (1, "UAT", 12, None)],
            True,
        ),
    ],
)
def test_pointer_retirement_refuses_to_lose_an_unmatched_selection(pointers, deployments, rejected):
    sql = (
        migration_root()
        .joinpath("V039__schema_descriptions_and_pointer_retirement.sql")
        .read_text(encoding="utf-8")
    )
    predicate = re.search(r"IF EXISTS \((.*?)\)\s*BEGIN;", sql, re.DOTALL)[1]
    predicate = re.sub(r" WITH \((?:TABLOCKX, )?HOLDLOCK\)", "", predicate)
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            ATTACH ':memory:' AS pricing;
            CREATE TABLE pricing.PRICING_PACKAGE_POINTER (
                model_id INTEGER, pointer_name TEXT, rate_package_id INTEGER
            );
            CREATE TABLE pricing.PRICING_MODEL_DEPLOYMENT (
                model_id INTEGER, deployment_slot TEXT,
                rate_package_id INTEGER, effective_to_ts TEXT
            );
        """)
        connection.executemany(
            "INSERT INTO pricing.PRICING_PACKAGE_POINTER VALUES (?, ?, ?)", pointers
        )
        connection.executemany(
            "INSERT INTO pricing.PRICING_MODEL_DEPLOYMENT VALUES (?, ?, ?, ?)", deployments
        )
        assert bool(connection.execute(predicate).fetchall()) is rejected
