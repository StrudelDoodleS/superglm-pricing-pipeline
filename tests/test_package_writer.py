"""SQL Server publication transaction regression tests.

The filename is historical; the concrete writer now lives in ``sqlserver.py``.
"""

from inspect import signature
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

from pricing_pipeline.publishing import sqlserver
from pricing_pipeline.publishing.identity import canonical_revision_metadata


def test_package_writer_does_not_write_deployment_tables_during_publish():
    writer = Path("src/pricing_pipeline/publishing/sqlserver.py").read_text(encoding="utf-8")

    assert "PRICING_MODEL_DEPLOYMENT" not in writer
    assert "PRICING_PACKAGE_POINTER" not in writer


def test_publish_rating_package_accepts_revision_mapping_without_public_status():
    parameters = signature(sqlserver.publish_sqlserver).parameters

    assert tuple(parameters) == ("engine", "prepared", "tables")
    assert "package_status" not in parameters
    assert "draft_validator" not in parameters
    assert "package_lineage_writer" not in parameters


def test_package_writer_canonicalises_revision_metadata_mapping_once():
    value = {"unicode": "München", "kind": "SUPERGLM_EDITOR"}

    assert canonical_revision_metadata(value) == ('{"kind":"SUPERGLM_EDITOR","unicode":"München"}')


def test_package_writer_accepts_non_dict_revision_metadata_mapping():
    value = MappingProxyType({"kind": "SUPERGLM_EDITOR"})

    assert canonical_revision_metadata(value) == '{"kind":"SUPERGLM_EDITOR"}'


def test_package_writer_rejects_non_mapping_revision_metadata():
    with pytest.raises(ValueError, match="revision_metadata must be a mapping"):
        canonical_revision_metadata('{"kind":"SUPERGLM_EDITOR"}')


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_package_writer_rejects_non_finite_revision_metadata(value):
    with pytest.raises(ValueError, match="finite numbers"):
        canonical_revision_metadata({"metric": value})


@pytest.mark.parametrize(
    "revision_metadata",
    [{1: "value"}, {"nested": {1: "value"}}],
    ids=["top-level", "nested"],
)
def test_package_writer_rejects_non_string_revision_metadata_keys(revision_metadata):
    with pytest.raises(ValueError, match="keys must be strings"):
        canonical_revision_metadata(revision_metadata)


def test_package_writer_rejects_non_json_serializable_revision_metadata():
    with pytest.raises(ValueError, match="JSON-serializable values"):
        canonical_revision_metadata({"unsupported": object()})


@pytest.fixture
def emitted_band_compile_sql():
    writer = Path("src/pricing_pipeline/publishing/sqlserver.py").read_text(encoding="utf-8")
    return " ".join(writer.split())


def test_package_writer_compiles_only_interval_offset_factors_as_bands(
    emitted_band_compile_sql,
):
    assert (
        "t.term_type = 'OFFSET_FACTOR' AND ls.level_set_type IN ('NUMERIC_BAND', 'SPLINE_GRID_1D')"
    ) in emitted_band_compile_sql


def test_package_writer_opens_only_the_terminal_compiled_band(emitted_band_compile_sql):
    assert (
        "CASE WHEN ROW_NUMBER() OVER ( PARTITION BY t.term_id ORDER BY "
        "CASE WHEN fl.lower_bound IS NULL THEN 1 ELSE 0 END, "
        "fl.lower_bound DESC, COALESCE(fl.order_index, 0) DESC, "
        "fl.feature_level_id DESC ) = 1 THEN NULL ELSE fl.upper_bound END"
    ) in emitted_band_compile_sql


class _Transaction:
    def __init__(self):
        self.connection = object()
        self.active = False

    def __enter__(self):
        self.active = True
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        self.active = False
        return False


class _Engine:
    def __init__(self):
        self.transaction = _Transaction()

    def begin(self):
        return self.transaction


def test_publish_sqlserver_runs_explicit_stages_inside_one_transaction(monkeypatch):
    engine = _Engine()
    events = []
    prepared = SimpleNamespace(
        build=SimpleNamespace(export_id="export-1"),
        verification=object(),
    )
    tables = object()
    package = SimpleNamespace(rate_package_id=42)
    expected = object()

    def stage(name, result=None):
        def run(*args, **kwargs):
            assert engine.transaction.active
            assert args[0] is engine.transaction.connection
            events.append(name)
            return result

        return run

    monkeypatch.setattr(sqlserver, "_lock_export", stage("lock"))
    monkeypatch.setattr(sqlserver, "_resolve_existing_or_equivalent", stage("resolve"))
    monkeypatch.setattr(sqlserver, "_replace_staging_frames", stage("stage"))
    monkeypatch.setattr(sqlserver, "_insert_draft_package", stage("draft", package))
    monkeypatch.setattr(sqlserver, "_insert_rating_tables", stage("rating"))
    monkeypatch.setattr(sqlserver, "_insert_lineage", stage("lineage", 501))
    monkeypatch.setattr(sqlserver, "_verify_draft", stage("verify"))
    monkeypatch.setattr(sqlserver, "_mark_published", stage("publish"))
    monkeypatch.setattr(sqlserver, "_delete_staging_children", stage("cleanup"))
    monkeypatch.setattr(
        sqlserver,
        "_publication_result",
        lambda package, model_run_id, prepared: events.append("result") or expected,
    )

    assert sqlserver.publish_sqlserver(engine, prepared, tables) is expected
    assert engine.transaction.active is False
    assert events == [
        "lock",
        "resolve",
        "stage",
        "draft",
        "rating",
        "lineage",
        "verify",
        "publish",
        "cleanup",
        "result",
    ]


def test_package_writer_and_sqlserver_reject_missing_staging_digest():
    conflicts = sqlserver._existing_export_conflicts(
        {
            "model_version": "v1",
            "effective_from_date": None,
            "effective_to_date": None,
            "source_file": "/tmp/rating.xlsx",
            "publication_receipt_sha256": "a" * 64,
            "staging_content_sha256": None,
            "parent_rate_package_id": None,
            "revision_metadata_json": None,
        },
        {
            "model_version": "v1",
            "effective_from_date": None,
            "effective_to_date": None,
            "source_file": "/tmp/rating.xlsx",
            "publication_receipt_sha256": "a" * 64,
            "staging_content_sha256": "b" * 64,
        },
        parent_rate_package_id=None,
        revision_metadata_json=None,
    )

    assert any("staging_content_sha256" in conflict for conflict in conflicts)


def test_package_writer_publishes_receipt_and_term_metadata_columns():
    writer = Path("src/pricing_pipeline/publishing/sqlserver.py").read_text(encoding="utf-8")

    for field in (
        "publication_receipt_json",
        "publication_receipt_sha256",
        "package_metadata_json",
        "revision_metadata_json",
        "offset_handling",
        "STG_TERM_METADATA",
        "term_metadata_json",
    ):
        assert field in writer
