"""SQL Server publication transaction regression tests.

The filename is historical; the concrete writer now lives in ``sqlserver.py``.
"""

import re
from inspect import signature
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pandas as pd
import pytest

from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild
from pricing_pipeline.publishing import sqlserver
from pricing_pipeline.publishing.identity import canonical_revision_metadata
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
    SuperGLMPublicationReceipt,
    write_publication_receipt,
)
from pricing_pipeline.publishing.publish import PublicationRequest, prepare_publication
from pricing_pipeline.publishing.rating_tables import prepare_rating_tables
from pricing_pipeline.workbench.submission import sha256_file


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


class _DraftResult:
    def __init__(self, *, row=None, scalar=None):
        self.row = row
        self.scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row

    def scalar_one(self):
        return self.scalar


_DEFAULT_RESERVATION = object()


class _DraftConnection:
    def __init__(self, *, reservation=_DEFAULT_RESERVATION):
        self.reservation = (
            {"model_version": "v1"} if reservation is _DEFAULT_RESERVATION else reservation
        )
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))
        if "FROM pricing.PRICING_MODEL_VERSION_RESERVATION" in sql:
            return _DraftResult(row=self.reservation)
        if "SELECT ISNULL(MAX(package_version), 0) + 1" in sql:
            return _DraftResult(scalar=3)
        if "INSERT INTO pricing.PRICING_RATE_PACKAGE" in sql:
            return _DraftResult(scalar=42)
        return _DraftResult()


class _DraftTransaction:
    def __init__(self, connection):
        self.connection = connection
        self.active = False
        self.exit_exception = None

    def __enter__(self):
        self.active = True
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        self.active = False
        self.exit_exception = exc
        return False


class _DraftEngine:
    def __init__(self, *, reservation=_DEFAULT_RESERVATION):
        self.connection = _DraftConnection(reservation=reservation)
        self.transaction = _DraftTransaction(self.connection)

    def begin(self):
        return self.transaction


def _real_prepared_rating_tables(tmp_path):
    model_config = ModelBuildConfig(
        model_name="MTPL_FREQ",
        model_label="MTPL frequency",
        target_name="ClaimNb",
        model_type="superglm_poisson",
        deployment_slot="MTPL_FREQ_UAT",
    )
    workbook = tmp_path / "rating_tables.xlsx"
    raw = pd.DataFrame([[None] * 3 for _ in range(8)])
    raw.iat[1, 2] = 0.123
    raw.iat[4, 0] = "TermMonths"
    raw.iloc[6, 0:3] = ["TermMonths", "Relativity", "Weight"]
    raw.iloc[7, 0:3] = ["12", 1.0, 10.0]
    raw.to_excel(workbook, sheet_name="Rating Tables", header=False, index=False)
    receipt = SuperGLMPublicationReceipt(
        schema_name="superglm_publication_receipt",
        schema_version=1,
        metadata_origin="SUPERGLM_FITTED_MODEL",
        superglm_version="1.0.0",
        extractor_version="unit-test",
        package_metadata={"model": {"family": "poisson", "link": "log"}},
        term_metadata={"TermMonths": {"feature_kind": "offset", "source_column": "Exposure"}},
        offset_contract=OffsetExportContract(
            handling="EXPORTED_FACTOR",
            source_factor_name="term_months",
            published_factor_name="TermMonths",
            source_name="Exposure",
            label="Policy exposure term",
        ),
    )
    receipt_path = tmp_path / "publication_receipt.json"
    receipt_sha256 = write_publication_receipt(receipt, receipt_path)
    build = ApprovedModelBuild(
        model_id=17,
        model_name=model_config.model_name,
        model_version="v1",
        model_type=model_config.model_type,
        target_name=model_config.target_name,
        deployment_slot=model_config.deployment_slot,
        manifest_id="manifest-1",
        export_id="export-1",
        rating_workbook_path=str(workbook),
        rating_workbook_sha256=sha256_file(workbook),
        effective_from="2026-08-28",
        created_by="pytest",
        publication_receipt_path=str(receipt_path),
        publication_receipt_sha256=receipt_sha256,
        candidate_artifact_path=str(tmp_path / "candidate.joblib"),
        candidate_artifact_sha256="a" * 64,
        candidate_artifact_format="superglm-candidate-joblib-v2",
        candidate_artifact_size_bytes=1,
        candidate_python_version="3.14.4",
        candidate_superglm_version="1.0.0",
        model_source_sha256="b" * 64,
        model_frame_sha256="c" * 64,
    )
    tables = prepare_rating_tables(
        workbook_path=workbook,
        build=build,
        model_config=model_config,
        effective_to=None,
    )
    build = build.model_copy(update={"model_equivalence_sha256": tables.model_equivalence_sha256})
    prepared = prepare_publication(
        PublicationRequest(
            build=build,
            model_config=model_config,
            execution_name="test",
            execution_id=build.export_id,
            allowed_artifact_root=None,
            revision_metadata={"kind": "RAW"},
        )
    )
    return prepared, tables


def _run_remote_draft(monkeypatch, prepared, tables, *, engine=None, lineage=None):
    engine = _DraftEngine() if engine is None else engine
    monkeypatch.setattr(sqlserver, "_resolve_existing_or_equivalent", lambda *args: None)
    monkeypatch.setattr(sqlserver, "_replace_staging_frames", lambda *args: None)
    monkeypatch.setattr(sqlserver, "_insert_rating_tables", lambda *args: None)
    monkeypatch.setattr(
        sqlserver,
        "_insert_lineage",
        (lambda *args: 501) if lineage is None else lineage,
    )
    return engine, sqlserver.publish_sqlserver(engine, prepared, tables)


def test_package_writer_rejects_replaced_staging_before_lineage_write(
    monkeypatch,
    tmp_path,
):
    prepared, tables = _real_prepared_rating_tables(tmp_path)
    tables.export_frame.loc[0, "source_file"] = str(tmp_path / "other.xlsx")
    lineage_calls = []
    engine = _DraftEngine()

    with pytest.raises(ValueError, match="release identity changed.*source_file"):
        _run_remote_draft(
            monkeypatch,
            prepared,
            tables,
            engine=engine,
            lineage=lambda *args: lineage_calls.append(args),
        )

    assert lineage_calls == []
    assert not any(
        "INSERT INTO pricing.PRICING_RATE_PACKAGE" in sql
        for sql, _params in engine.connection.statements
    )


def test_package_writer_reserves_staged_version_for_direct_root_publication(
    monkeypatch,
    tmp_path,
):
    prepared, tables = _real_prepared_rating_tables(tmp_path)
    engine = _DraftEngine(reservation=None)

    assert "model_id" not in tables.export_frame.columns
    assert "staging_content_sha256" not in tables.export_frame.columns
    engine, result = _run_remote_draft(
        monkeypatch,
        prepared,
        tables,
        engine=engine,
    )
    connection = engine.connection

    reservation = next(
        item
        for item in connection.statements
        if "INSERT INTO pricing.PRICING_MODEL_VERSION_RESERVATION" in item[0]
    )
    package = next(
        item
        for item in connection.statements
        if "INSERT INTO pricing.PRICING_RATE_PACKAGE" in item[0]
    )
    reservation_query = next(
        sql
        for sql, _params in connection.statements
        if "FROM pricing.PRICING_MODEL_VERSION_RESERVATION" in sql
    )
    assert "WITH (UPDLOCK, HOLDLOCK)" in reservation_query
    assert reservation[1] == {
        "model_id": 17,
        "export_id": "export-1",
        "model_version": "v1",
    }
    assert connection.statements.index(reservation) < connection.statements.index(package)
    package_sql, package_params = package
    bind_names = set(re.findall(r":([a-z0-9_]+)", package_sql))
    assert bind_names <= package_params.keys()
    export = tables.export_frame.iloc[0]
    assert package_params == {
        "parent_rate_package_id": None,
        "model_id": prepared.build.model_id,
        "model_name": prepared.build.model_name,
        "model_version": prepared.build.model_version,
        "package_version": 3,
        "base_rate": export["base_rate"],
        "effective_from_date": prepared.build.effective_from,
        "effective_to_date": prepared.effective_to,
        "package_status": "DRAFT",
        "source_export_id": prepared.build.export_id,
        "source_file": str(Path(prepared.build.rating_workbook_path).resolve()),
        "publication_receipt_json": export["publication_receipt_json"],
        "publication_receipt_sha256": prepared.build.publication_receipt_sha256,
        "staging_content_sha256": tables.staging_content_sha256,
        "package_metadata_json": export["package_metadata_json"],
        "revision_metadata_json": canonical_revision_metadata(prepared.revision_metadata),
        "offset_handling": export["offset_handling"],
        "offset_factor_name": export["offset_factor_name"],
        "offset_source_name": export["offset_source_name"],
        "offset_label": export["offset_label"],
        "metadata_origin": export["metadata_origin"],
        "created_by": prepared.build.created_by,
    }
    assert result.rate_package_id == 42
    assert result.model_run_id == 501


def test_package_writer_rejects_root_package_with_different_reserved_version(tmp_path):
    prepared, tables = _real_prepared_rating_tables(tmp_path)
    connection = _DraftConnection(reservation={"model_version": "v2"})

    with pytest.raises(ValueError, match="reserved model_version.*v2.*v1"):
        sqlserver._insert_draft_package(connection, prepared, tables)

    assert not any(
        "INSERT INTO pricing.PRICING_RATE_PACKAGE" in sql for sql, _params in connection.statements
    )


def test_successful_publish_deletes_staging_payload_after_final_status_only(
    monkeypatch,
    tmp_path,
):
    prepared, tables = _real_prepared_rating_tables(tmp_path)

    engine, _result = _run_remote_draft(monkeypatch, prepared, tables)

    statements = [sql for sql, _params in engine.connection.statements]
    status_index = next(
        index
        for index, sql in enumerate(statements)
        if "UPDATE pricing.PRICING_RATE_PACKAGE" in sql
    )
    payload_deletes = [
        (index, " ".join(sql.split()))
        for index, sql in enumerate(statements)
        if sql.lstrip().startswith("DELETE FROM pricing_stg.")
    ]
    assert payload_deletes == [
        (
            status_index + 1,
            "DELETE FROM pricing_stg.STG_TERM_METADATA WHERE export_id = :export_id",
        ),
        (
            status_index + 2,
            "DELETE FROM pricing_stg.STG_CELL_LEVEL WHERE export_id = :export_id",
        ),
        (
            status_index + 3,
            "DELETE FROM pricing_stg.STG_RATE_CELL WHERE export_id = :export_id",
        ),
    ]
    assert not any("DELETE FROM pricing_stg.STG_RATING_EXPORT" in sql for sql in statements)


def test_package_lineage_failure_prevents_final_status_and_rolls_back_transaction(
    monkeypatch,
    tmp_path,
):
    prepared, tables = _real_prepared_rating_tables(tmp_path)
    engine = _DraftEngine()
    failure = RuntimeError("lineage write failed")

    def fail_lineage(*_args):
        raise failure

    with pytest.raises(RuntimeError, match="lineage write failed"):
        _run_remote_draft(
            monkeypatch,
            prepared,
            tables,
            engine=engine,
            lineage=fail_lineage,
        )

    assert engine.transaction.exit_exception is failure
    assert any(
        "INSERT INTO pricing.PRICING_RATE_PACKAGE" in sql
        for sql, _params in engine.connection.statements
    )
    assert not any(
        "UPDATE pricing.PRICING_RATE_PACKAGE" in sql
        for sql, _params in engine.connection.statements
    )
    assert not any(
        sql.lstrip().startswith("DELETE FROM pricing_stg.")
        for sql, _params in engine.connection.statements
    )


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


def _existing_package_row(prepared, tables, **overrides):
    build = prepared.build
    row = {
        "rate_package_id": 42,
        "package_version": 3,
        "model_id": build.model_id,
        "model_name": build.model_name,
        "model_version": build.model_version,
        "effective_from_date": build.effective_from,
        "effective_to_date": prepared.effective_to,
        "package_status": "PUBLISHED",
        "source_export_id": build.export_id,
        "source_file": str(Path(build.rating_workbook_path).resolve()),
        "publication_receipt_sha256": build.publication_receipt_sha256,
        "staging_content_sha256": tables.staging_content_sha256,
        "parent_rate_package_id": prepared.parent_rate_package_id,
        "revision_metadata_json": canonical_revision_metadata(prepared.revision_metadata),
    }
    row.update(overrides)
    return row


class _ExistingPackageConnection:
    def __init__(self, row):
        self.row = row
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))
        if "source_export_id = :export_id" in sql:
            return _DraftResult(row=self.row)
        raise AssertionError(f"unexpected SQL after existing-package resolution: {sql}")


def _assert_existing_package_conflict(tmp_path, **overrides):
    prepared, tables = _real_prepared_rating_tables(tmp_path)
    connection = _ExistingPackageConnection(_existing_package_row(prepared, tables, **overrides))
    with pytest.raises(ValueError, match="incompatible metadata") as error:
        sqlserver._resolve_existing_or_equivalent(connection, prepared, tables)
    return str(error.value), connection


def test_package_writer_rejects_existing_source_export_with_different_model_version(tmp_path):
    message, connection = _assert_existing_package_conflict(tmp_path, model_version="v2")

    assert "model_version" in message
    assert len(connection.statements) == 1


def test_package_writer_rejects_existing_source_export_with_different_effective_from(tmp_path):
    message, _connection = _assert_existing_package_conflict(
        tmp_path,
        effective_from_date="2026-08-29",
    )

    assert "effective_from_date" in message


def test_package_writer_rejects_existing_source_export_with_different_source_file(tmp_path):
    message, _connection = _assert_existing_package_conflict(
        tmp_path,
        source_file=str(tmp_path / "other" / "rating_tables.xlsx"),
    )

    assert "source_file" in message


def test_package_writer_rejects_existing_source_export_with_different_receipt_hash(tmp_path):
    message, _connection = _assert_existing_package_conflict(
        tmp_path,
        publication_receipt_sha256=None,
    )

    assert "publication_receipt_sha256" in message


def test_package_writer_and_sqlserver_reject_missing_staging_digest(tmp_path):
    message, _connection = _assert_existing_package_conflict(
        tmp_path,
        staging_content_sha256=None,
    )

    assert "staging_content_sha256" in message


def test_package_writer_rejects_existing_package_built_from_other_rate_content(tmp_path):
    message, _connection = _assert_existing_package_conflict(
        tmp_path,
        staging_content_sha256="d" * 64,
    )

    assert "staging_content_sha256" in message


def test_existing_draft_package_retains_staging_payload_for_recovery(tmp_path):
    prepared, tables = _real_prepared_rating_tables(tmp_path)
    connection = _ExistingPackageConnection(
        _existing_package_row(prepared, tables, package_status="DRAFT")
    )

    with pytest.raises(RuntimeError, match="existing model package is not PUBLISHED"):
        sqlserver._resolve_existing_or_equivalent(connection, prepared, tables)

    assert not any(
        sql.lstrip().startswith("DELETE FROM pricing_stg.")
        for sql, _params in connection.statements
    )


def test_existing_published_package_cleans_retry_payload_but_retains_header(
    monkeypatch,
    tmp_path,
):
    prepared, tables = _real_prepared_rating_tables(tmp_path)
    engine = _DraftEngine()
    expected = object()
    monkeypatch.setattr(
        sqlserver,
        "_resolve_existing_or_equivalent",
        lambda *args: expected,
    )
    monkeypatch.setattr(
        sqlserver,
        "_replace_staging_frames",
        lambda *args: pytest.fail("existing publication must not replace staging"),
    )

    result = sqlserver.publish_sqlserver(engine, prepared, tables)

    assert result is expected
    deletes = [
        " ".join(sql.split())
        for sql, _params in engine.connection.statements
        if sql.lstrip().startswith("DELETE FROM pricing_stg.")
    ]
    assert deletes == [
        "DELETE FROM pricing_stg.STG_TERM_METADATA WHERE export_id = :export_id",
        "DELETE FROM pricing_stg.STG_CELL_LEVEL WHERE export_id = :export_id",
        "DELETE FROM pricing_stg.STG_RATE_CELL WHERE export_id = :export_id",
    ]
    assert not any("STG_RATING_EXPORT" in sql for sql in deletes)


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
