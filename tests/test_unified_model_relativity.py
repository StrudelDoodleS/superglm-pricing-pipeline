"""The final model view contains lookup entries and exact spline segments."""

import json
import re

import pandas as pd
import pytest
from sqlalchemy import text

from pricing_pipeline.publishing.rating_tables import RatingTables
from pricing_pipeline.publishing.sqlite import _insert_local_rating_tables
from pricing_pipeline.resources import migration_root
from tests.test_ppform_sql_persistence import _tables
from tests.test_ppform_sql_persistence import engine as segment_engine


@pytest.fixture
def engine(tmp_path):
    yield from segment_engine.__wrapped__(tmp_path)


def _lookup_tables():
    return RatingTables(
        pd.DataFrame(),
        pd.DataFrame(
            [
                {
                    "export_id": "exp",
                    "row_id": i,
                    "term_name": name,
                    "term_type": kind,
                    "sequence_no": i + 1,
                    "cell_key_text": f"{name}={level}",
                    "multiplier": multiplier,
                    "log_coefficient": coefficient,
                    "exposure_weight": 20,
                    "record_count": None,
                    "is_default": 0,
                    "is_reference": 0,
                }
                for i, (name, kind, level, multiplier, coefficient) in enumerate(
                    [
                        ("region", "CATEGORICAL_MAIN", "A", 1.2, 0.1823215568),
                        ("distance", "NUMERIC_MAIN", "per_unit", 1.1, 0.0953101798),
                        ("exposure", "OFFSET_FACTOR", "per_unit", 1.0, 0.0),
                    ],
                    1,
                )
            ]
        ),
        pd.DataFrame(),
        pd.DataFrame(
            [
                {
                    "term_name": "exposure",
                    "term_metadata_json": '{"rating_representation":"PER_UNIT_FACTOR"}',
                }
            ]
        ),
        "a" * 64,
        "b" * 64,
    )


def test_final_view_contains_each_effect_once_with_explicit_representation(engine):
    with engine.begin() as c:
        _insert_local_rating_tables(c, {"rate_package_id": 1}, _tables())
        _insert_local_rating_tables(c, {"rate_package_id": 1}, _lookup_tables())
        rows = (
            c.execute(
                text("""
            SELECT * FROM pricing.V_FINAL_MODEL_RELATIVITY
            WHERE rate_package_id=1 ORDER BY term_sequence_no, level_sort_order
        """)
            )
            .mappings()
            .all()
        )
        assert len(rows) == 7
        spline = [r for r in rows if r["representation"] == "SPLINE"]
        assert len(spline) == 4
        assert all(r["relativity"] is None and r["log_coefficient"] is None for r in spline)
        assert spline[1]["a"] == 1 and spline[1]["d"] == 4
        assert spline[1]["lower_bound"] == 0.12345678912345
        assert spline[0]["feature_name"] == "x"
        assert json.loads(spline[0]["transforms_json"])["x"]["source"] == "raw"
        assert "model_completed_ts" in spline[0]
        assert all(r["upper_inclusive"] == 0 for r in spline)
        kinds = {r["term_name"]: r["representation"] for r in rows}
        assert kinds == {
            "curve": "SPLINE",
            "region": "LOOKUP",
            "distance": "NUMERIC",
            "exposure": "PER_UNIT_FACTOR",
        }
        lookup = next(r for r in rows if r["term_name"] == "region")
        assert lookup["relativity"] == 1.2
        assert lookup["a"] is None and lookup["upper_inclusive"] is None


def test_published_and_deployed_views_include_splines_without_other_packages(engine):
    with engine.begin() as c:
        _insert_local_rating_tables(c, {"rate_package_id": 1}, _tables(tails=False))
        _insert_local_rating_tables(c, {"rate_package_id": 2}, _tables(shift=10))
        c.execute(
            text(
                "UPDATE pricing.PRICING_RATE_PACKAGE SET package_status='PUBLISHED' WHERE rate_package_id=1"
            )
        )
        c.execute(
            text("""
            INSERT INTO pricing.PRICING_MODEL_DEPLOYMENT (
                model_id, rate_package_id, deployment_slot, effective_from_ts, deployed_by
            ) VALUES (1,1,'TEST','2026-09-01','pytest')
        """)
        )
        for view in [
            "V_MODEL_CANDIDATE_RELATIVITY",
            "V_PUBLISHED_MODEL_RELATIVITY",
            "V_CURRENT_DEPLOYED_RELATIVITY",
        ]:
            rows = (
                c.execute(text(f"SELECT * FROM pricing.{view} ORDER BY level_sort_order"))
                .mappings()
                .all()
            )
            assert len(rows) == 2
            assert {r["rate_package_id"] for r in rows} == {1}
            assert {r["representation"] for r in rows} == {"SPLINE"}
            assert rows[-1]["upper_inclusive"] == 1


def test_sql_server_unified_projection_returns_both_representations(engine):
    sql = (migration_root() / "V044__unified_final_model_relativity.sql").read_text()
    definition = re.search(
        r"CREATE OR ALTER VIEW pricing.V_FINAL_MODEL_RELATIVITY\s+AS\s+(.*?)(?=\nGO)",
        sql,
        re.DOTALL,
    ).group(1)
    # Execute the shipped SELECT with SQLite equivalents for SQL Server's
    # JSON/count functions. This does not compile the view on SQL Server.
    query = (
        definition.replace("COUNT_BIG(", "COUNT(")
        .replace("JSON_QUERY(", "json_extract(")
        .replace("JSON_VALUE(", "json_extract(")
    )
    with engine.begin() as c:
        _insert_local_rating_tables(c, {"rate_package_id": 1}, _tables())
        _insert_local_rating_tables(c, {"rate_package_id": 1}, _lookup_tables())
        rows = c.execute(text(query)).mappings().all()
        assert len(rows) == 7
        assert sum(r["representation"] == "SPLINE" for r in rows) == 4
        assert all(r["relativity"] is None for r in rows if r["representation"] == "SPLINE")
        assert next(r for r in rows if r["term_name"] == "region")["relativity"] == 1.2
        assert (
            next(r for r in rows if r["term_name"] == "exposure")["representation"]
            == "PER_UNIT_FACTOR"
        )


def test_unmarked_offset_named_per_unit_remains_a_lookup(engine):
    tables = _lookup_tables()
    tables.term_metadata.loc[:, "term_metadata_json"] = '{"rating_representation":"LOOKUP"}'
    with engine.begin() as c:
        _insert_local_rating_tables(c, {"rate_package_id": 1}, tables)
        for metadata in ('{"rating_representation":"LOOKUP"}', None):
            c.execute(
                text(
                    "UPDATE pricing.PRICING_TERM SET term_metadata_json=:metadata WHERE term_name='exposure'"
                ),
                {"metadata": metadata},
            )
            assert (
                c.execute(
                    text(
                        "SELECT representation FROM pricing.V_FINAL_MODEL_RELATIVITY WHERE term_name='exposure'"
                    )
                ).scalar_one()
                == "LOOKUP"
            )
