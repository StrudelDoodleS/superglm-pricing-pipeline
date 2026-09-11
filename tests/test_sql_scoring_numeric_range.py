"""Execute the scorer's numeric expressions with strict exponential overflow.

These tests use the active procedure's expressions, not a second scoring
implementation. SQLite supplies the SQL evaluator; SQL Server procedure and
query-plan execution still need an integration check.
"""

import math
import re
import sqlite3

import pytest

from pricing_pipeline.resources import migration_root


def _scorer_sql():
    definition = None
    for migration in sorted(migration_root().glob("V*.sql")):
        sql = migration.read_text(encoding="utf-8")
        match = re.search(
            r"CREATE OR ALTER PROCEDURE pricing\.PREDICT_RATE_PACKAGE\b.*?(?=\nGO|\Z)",
            sql,
            flags=re.DOTALL,
        )
        if match:
            definition = match[0]
    assert definition is not None
    return definition


def _numeric_rows(connection, sql, inputs):
    projection = re.search(
        r"'NUMERIC',.*?feature_level\.level_code,\s*(.*?)\s+FROM pricing\.",
        sql,
        flags=re.DOTALL,
    )[1]
    connection.executescript("""
        CREATE TABLE numeric_input (term_id INTEGER, numeric_value REAL);
        CREATE TABLE cell (term_id INTEGER, log_coefficient REAL);
    """)
    for term_id, (value, coefficient) in enumerate(inputs):
        connection.execute("INSERT INTO numeric_input VALUES (?, ?)", (term_id, value))
        connection.execute("INSERT INTO cell VALUES (?, ?)", (term_id, coefficient))
    return connection.execute(
        f"SELECT {projection} FROM numeric_input JOIN cell USING (term_id) ORDER BY term_id"
    ).fetchall()


def _connection():
    connection = sqlite3.connect(":memory:")
    # SQLite's built-in EXP may return infinity. SQL Server rejects overflow.
    connection.create_function("EXP", 1, lambda value: None if value is None else math.exp(value))
    connection.create_function("LOG", 1, lambda value: None if value is None else math.log(value))
    return connection


@pytest.mark.parametrize(
    ("inputs", "expected_relativity"),
    [
        ([(1000, 1), (1000, -1)], 1.0),
        ([(1000, 1), (999, -1)], math.e),
        ([(2, 0.2), (4, -0.1)], 1.0),
    ],
)
def test_numeric_score_combines_logs_before_exponentiating(inputs, expected_relativity):
    sql = _scorer_sql()
    with _connection() as connection:
        rows = _numeric_rows(connection, sql, inputs)
        connection.execute("CREATE TABLE matched (multiplier REAL, log_coefficient REAL)")
        connection.executemany("INSERT INTO matched VALUES (?, ?)", rows)
        summary = re.search(
            r"SELECT\s+@model_name AS model_name,.*?FROM @matched;", sql, flags=re.DOTALL
        )[0].replace("FROM @matched", "FROM matched")
        result = connection.execute(
            summary,
            {
                "model_name": "TEST",
                "rate_package_id": 1,
                "base_rate": 2.0,
                "exposure": 0.5,
                "required_terms": len(inputs),
                "matched_terms": len(inputs),
            },
        ).fetchone()
        assert result[4] == pytest.approx(expected_relativity)
        assert result[5] == pytest.approx(expected_relativity)


@pytest.mark.parametrize(
    ("log_contribution", "expected_multiplier"),
    [
        (0.0, 1.0),
        (2.0, math.exp(2)),
        (-2.0, math.exp(-2)),
        (709.0, math.exp(709)),
        (-708.0, math.exp(-708)),
        (math.log(1.79e308), math.exp(math.log(1.79e308))),
        (math.nextafter(math.log(1.79e308), math.inf), None),
        (math.log(2.23e-308), math.exp(math.log(2.23e-308))),
        (math.nextafter(math.log(2.23e-308), -math.inf), None),
        (1000.0, None),
        (-1000.0, None),
    ],
)
def test_numeric_breakdown_preserves_log_when_multiplier_is_out_of_range(
    log_contribution, expected_multiplier
):
    sql = _scorer_sql()
    breakdown = re.search(
        r"IF @include_breakdown = 1\s+BEGIN\s+(SELECT.*?FROM @matched\s+ORDER BY term_id;)",
        sql,
        flags=re.DOTALL,
    )[1].replace("FROM @matched", "FROM matched")
    with _connection() as connection:
        row = _numeric_rows(connection, sql, [(log_contribution, 1)])[0]
        connection.executescript("""
            CREATE TABLE matched (
                term_id INTEGER, term_name TEXT, term_type TEXT, match_type TEXT,
                feature_name TEXT, input_value TEXT, level_code TEXT,
                multiplier REAL, log_coefficient REAL
            );
        """)
        connection.execute(
            "INSERT INTO matched VALUES (1, 'x', 'NUMERIC_MAIN', 'NUMERIC', 'x', ?, 'per_unit', ?, ?)",
            (str(log_contribution), *row),
        )
        result = connection.execute(breakdown).fetchone()
        if expected_multiplier is None:
            assert result[7] is None
        else:
            assert result[7] == pytest.approx(expected_multiplier, abs=0)
        assert result[8] == log_contribution


@pytest.mark.parametrize("match_type", ["BAND", "INTERACTION", "CELL", "DEFAULT"])
def test_breakdown_preserves_exported_multiplier_for_other_effects(match_type):
    sql = _scorer_sql()
    breakdown = re.search(
        r"IF @include_breakdown = 1\s+BEGIN\s+(SELECT.*?FROM @matched\s+ORDER BY term_id;)",
        sql,
        flags=re.DOTALL,
    )[1].replace("FROM @matched", "FROM matched")
    with _connection() as connection:
        connection.executescript("""
            CREATE TABLE matched (
                term_id INTEGER, term_name TEXT, term_type TEXT, match_type TEXT,
                feature_name TEXT, input_value TEXT, level_code TEXT,
                multiplier REAL, log_coefficient REAL
            );
        """)
        connection.execute(
            "INSERT INTO matched VALUES (1, 'region', 'CATEGORY', ?, 'region', 'A', 'A', 1.12, 0.1133)",
            (match_type,),
        )
        result = connection.execute(breakdown).fetchone()
        assert result[7:] == (1.12, 0.1133)
