"""Exercise exact segment persistence and the active scorer's SQL expressions."""

import json
import math
import re

import pandas as pd
import pytest
from sqlalchemy import text

from pricing_pipeline.infra.offline_sqlite import (
    apply_offline_ddl,
    sqlite_engine_with_offline_schemas,
)
from pricing_pipeline.publishing.rating_tables import RatingTables
from pricing_pipeline.publishing.sqlite import _insert_local_rating_tables
from pricing_pipeline.resources import migration_root


@pytest.fixture
def engine(tmp_path):
    engine = sqlite_engine_with_offline_schemas(
        {name: tmp_path / f"{name}.sqlite" for name in ("pricing", "pricing_stg", "mlops")}
    )
    apply_offline_ddl(engine)
    with engine.begin() as connection:
        connection.execute(
            text("""
            INSERT INTO pricing.PRICING_MODEL
                (model_id, model_name, model_label, target_name, model_type, created_by)
            VALUES (1, 'TEST', 'Test', 'y', 'superglm_poisson', 'pytest')
        """)
        )
        for package in (1, 2):
            connection.execute(
                text("""
                INSERT INTO pricing.PRICING_RATE_PACKAGE
                    (rate_package_id, model_id, model_name, model_version, package_version,
                     base_rate, package_status, package_metadata_json, created_by)
                VALUES (:package, 1, 'TEST', :version, :package, 1, 'LOCAL_AUDIT',
                        :metadata, 'pytest')
            """),
                {
                    "package": package,
                    "version": f"v{package}",
                    "metadata": json.dumps(
                        {
                            "input_preparation": {
                                "transforms": {"x": {"operation": "log", "source": "raw"}}
                            }
                        }
                    ),
                },
            )
    yield engine
    engine.dispose()


def _tables(*, shift=0, tails=True):
    segments = [
        (None, 0.12345678912345, 1 + shift, 0, 0, 0, 0),
        (0.12345678912345, 2.12345678912345, 1 + shift, 2, 3, 4, 0),
        (2.12345678912345, 5.12345678912345, 10 + shift, -2, 1, -0.5, int(not tails)),
        (5.12345678912345, None, 8.5 + shift, 0, 0, 0, 0),
    ]
    if not tails:
        segments = segments[1:-1]
    rate_rows, level_rows = [], []
    for order, (lower, upper, a, b, c, d, inclusive) in enumerate(segments, 1):
        rate_rows.append(
            {
                "export_id": "exp",
                "row_id": order,
                "term_name": "curve",
                "term_type": "SPLINE_PPOLY_1D",
                "sequence_no": 1,
                "cell_key_text": f"curve=segment-{order}",
                "multiplier": math.exp(a),
                "log_coefficient": a,
                "exposure_weight": 12.5,
                "record_count": None,
                "is_default": 0,
                "is_reference": 0,
                "spline_a": a,
                "spline_b": b,
                "spline_c": c,
                "spline_d": d,
                "spline_lower": lower,
                "spline_upper": upper,
                "spline_upper_inclusive": inclusive,
            }
        )
        level_rows.append(
            {
                "export_id": "exp",
                "row_id": order,
                "position_no": 1,
                "feature_name": "x",
                "level_code": f"segment-{order}",
                "level_label": f"Segment {order}",
                "order_index": order,
            }
        )
    return RatingTables(
        pd.DataFrame(),
        pd.DataFrame(rate_rows),
        pd.DataFrame(level_rows),
        pd.DataFrame([{"term_name": "curve", "term_metadata_json": '{"kind":"ppform"}'}]),
        "a" * 64,
        "b" * 64,
    )


def test_sqlite_persists_exact_segments_and_excludes_lookup_relativities(engine):
    with engine.begin() as connection:
        for package, shift in ((1, 0), (2, 10)):
            _insert_local_rating_tables(
                connection, {"rate_package_id": package}, _tables(shift=shift)
            )
        segments = (
            connection.execute(
                text("""
            SELECT * FROM pricing.V_MODEL_SPLINE_SEGMENT
            WHERE rate_package_id = 1 ORDER BY segment_order
        """)
            )
            .mappings()
            .all()
        )
        assert len(segments) == 4
        assert segments[0]["lower_bound"] is None
        assert segments[1]["lower_bound"] == 0.12345678912345
        assert segments[1]["a"] == 1
        assert segments[1]["d"] == 4
        assert segments[2]["upper_inclusive"] == 0
        assert segments[3]["upper_bound"] is None
        assert segments[0]["model_completed_ts"] is None
        assert segments[0]["feature_name"] == "x"
        assert segments[0]["level_label"] == "Segment 1"
        assert json.loads(segments[0]["transforms_json"])["x"]["source"] == "raw"
        assert segments[0]["term_metadata_json"] == '{"kind":"ppform"}'
        assert (
            connection.execute(text("SELECT count(*) FROM pricing.V_MODEL_RELATIVITY")).scalar()
            == 0
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM pricing.PRICING_COMPILED_RATE_CELL")
            ).scalar()
            == 8
        )
        assert (
            connection.execute(
                text(
                    "SELECT a FROM pricing.PRICING_SPLINE_SEGMENT WHERE rate_package_id=2 AND segment_order=1"
                )
            ).scalar()
            == 11
        )


def _spline_query():
    sql = None
    for path in sorted(migration_root().glob("V*.sql")):
        match = re.search(
            r"CREATE OR ALTER PROCEDURE pricing\.PREDICT_RATE_PACKAGE\b.*?(?=\nGO|\Z)",
            path.read_text(),
            re.DOTALL,
        )
        if match:
            sql = match[0]
    match = re.search(r"WITH spline_input AS \(.*?FROM spline_coordinate.*?;", sql, re.DOTALL)
    assert match is not None, "active scorer must evaluate exact spline segments"
    query = match[0]
    query = re.sub(r"INSERT INTO @matched \(.*?\)\s*", "", query, flags=re.DOTALL)
    query = query.replace("TRY_CONVERT(FLOAT, input_value)", "try_float(input_value)")
    query = query.replace("JSON_VALUE", "json_extract")
    query = query.replace("CONVERT(NVARCHAR(128), segment_order)", "CAST(segment_order AS TEXT)")
    return query


@pytest.mark.parametrize("tails", [False, True])
@pytest.mark.parametrize(
    "value",
    [
        None,
        "bad",
        -100,
        0.12345678912345,
        0.62345678912345,
        2.12345678912345,
        5.12345678912345,
        100,
    ],
)
def test_active_sql_spline_expression_matches_bounds_and_package(engine, tails, value):
    query = _spline_query()
    with engine.begin() as connection:
        _insert_local_rating_tables(connection, {"rate_package_id": 1}, _tables(tails=tails))
        _insert_local_rating_tables(connection, {"rate_package_id": 2}, _tables(shift=10))
        raw = connection.connection.driver_connection

        def try_float(value):
            try:
                return float(value)
            except ValueError, TypeError:
                return None

        raw.create_function("try_float", 1, try_float)
        raw.create_function("CONCAT", -1, lambda *args: "".join(str(arg) for arg in args))
        rows = raw.execute(
            query, {"features_json": json.dumps({"x": value}), "rate_package_id": 1}
        ).fetchall()
        lo, knot, hi = 0.12345678912345, 2.12345678912345, 5.12345678912345
        if value is None or value == "bad" or (not tails and (value < lo or value > hi)):
            assert rows == []
        else:
            if value < lo:
                expected = 1
            elif value < knot:
                u = (value - lo) / (knot - lo)
                expected = 1 + u * (2 + u * (3 + u * 4))
            elif value <= hi:
                u = (value - knot) / (hi - knot)
                expected = 10 + u * (-2 + u * (1 - u * 0.5))
            else:
                expected = 8.5
            assert len(rows) == 1
            assert rows[0][-1] == pytest.approx(expected)
            assert rows[0][3] == "SPLINE"


def test_sql_server_spline_view_uses_normalized_split_lineage():
    sql = (migration_root() / "V043__exact_spline_segments.sql").read_text()
    view = re.search(
        r"CREATE OR ALTER VIEW pricing\.V_MODEL_SPLINE_SEGMENT.*?(?=\nGO)", sql, re.DOTALL
    )[0]
    assert "mr.split_set_id" not in view
    assert "mlops.MODEL_RUN_SPLIT_SET" in view
    assert "dataset_role = 'training'" in view
    assert "split_role = 'validation'" in view


def test_sql_server_segments_have_frozen_package_write_guard():
    sql = (migration_root() / "V043__exact_spline_segments.sql").read_text()
    assert "CREATE OR ALTER TRIGGER pricing.TR_PRICING_SPLINE_SEGMENT_IMMUTABLE_WRITE" in sql
    assert "rp.package_status <> 'DRAFT'" in sql
    assert "FROM deleted" in sql
    assert "pricing.PRICING_MODEL_DEPLOYMENT" in sql


def test_sqlite_staging_upgrade_preserves_legacy_rows(engine):
    with engine.begin() as connection:
        for column in ("a", "b", "c", "d", "lower", "upper", "upper_inclusive"):
            connection.exec_driver_sql(
                f"ALTER TABLE pricing_stg.STG_RATE_CELL DROP COLUMN spline_{column}"
            )
        connection.execute(
            text("""
            INSERT INTO pricing_stg.STG_RATE_CELL
                (export_id, row_id, term_name, term_type, sequence_no, cell_key_text, multiplier, log_coefficient)
            VALUES ('old', 1, 'region', 'CATEGORICAL_MAIN', 1, 'region=A', 1, 0)
        """)
        )
    apply_offline_ddl(engine)
    apply_offline_ddl(engine)
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT spline_a, spline_upper_inclusive FROM pricing_stg.STG_RATE_CELL WHERE export_id='old'"
            )
        ).one() == (None, None)


def test_sql_server_segment_insert_preserves_staged_floats(engine):
    import ast
    import inspect

    from pricing_pipeline.publishing.sqlserver import _insert_rating_tables

    tree = ast.parse(inspect.getsource(_insert_rating_tables))
    statement = next(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and "INSERT INTO pricing.PRICING_SPLINE_SEGMENT" in node.value
    )
    insert = re.search(r"INSERT INTO pricing\.PRICING_SPLINE_SEGMENT.*?;", statement, re.DOTALL)[0]
    tables = _tables()
    with engine.begin() as connection:
        _insert_local_rating_tables(connection, {"rate_package_id": 1}, tables)
        expected = connection.execute(
            text("SELECT * FROM pricing.PRICING_SPLINE_SEGMENT ORDER BY segment_order")
        ).all()
        connection.execute(text("DELETE FROM pricing.PRICING_SPLINE_SEGMENT"))
        columns = list(tables.rate_cells.columns)
        connection.execute(
            text(
                "INSERT INTO pricing_stg.STG_RATE_CELL ("
                + ", ".join(columns)
                + ") VALUES ("
                + ", ".join(":" + column for column in columns)
                + ")"
            ),
            tables.rate_cells.astype(object)
            .where(pd.notna(tables.rate_cells), None)
            .to_dict("records"),
        )
        for level in tables.cell_levels.to_dict("records"):
            connection.execute(
                text("""
                INSERT INTO pricing_stg.STG_CELL_LEVEL
                    (export_id, row_id, position_no, feature_name, level_code, level_label, order_index,
                     feature_value_type, level_set_name, level_set_type)
                VALUES (:export_id, :row_id, :position_no, :feature_name, :level_code, :level_label,
                        :order_index, 'NUMERIC', 'x_spline', 'SPLINE_PPOLY_1D')
            """),
                level,
            )
        connection.execute(text(insert), {"export_id": "exp", "rate_package_id": 1})
        actual = connection.execute(
            text("SELECT * FROM pricing.PRICING_SPLINE_SEGMENT ORDER BY segment_order")
        ).all()
        assert actual == expected


def test_spline_segment_cannot_reference_another_package_term(engine):
    from sqlalchemy.exc import IntegrityError

    with engine.begin() as connection:
        _insert_local_rating_tables(connection, {"rate_package_id": 1}, _tables())
        with pytest.raises(IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                text("UPDATE pricing.PRICING_SPLINE_SEGMENT SET rate_package_id = 2")
            )
