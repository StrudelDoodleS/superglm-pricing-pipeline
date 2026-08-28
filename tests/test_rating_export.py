from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from pricing_pipeline.infra.offline_sqlite import (
    apply_offline_ddl,
    sqlite_engine_with_offline_schemas,
)
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.models.spec import ApprovedModelBuild, ModelExportResult
from pricing_pipeline.orchestration import pipeline
from pricing_pipeline.publishing import lineage, rating_tables, sqlserver
from pricing_pipeline.publishing import publish as publication
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
    SuperGLMPublicationReceipt,
    write_publication_receipt,
)
from pricing_pipeline.publishing.publish import CompletedModelPublishResult
from pricing_pipeline.publishing.rating_tables import RatingTables, prepare_rating_tables
from pricing_pipeline.workbench.artifacts import CandidateBundle, save_candidate_bundle

MODEL_CONFIG = ModelBuildConfig(
    model_name="MTPL_FREQ",
    model_label="MTPL frequency",
    target_name="ClaimNb",
    model_type="superglm_poisson",
    deployment_slot="MTPL_FREQ_UAT",
)


class _ExportModel:
    def __init__(self):
        self.calls = []

    def export_rating_tables(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        Path(args[0]).write_bytes(b"workbook")


def test_build_export_id_is_path_safe():
    export_id = rating_tables.build_export_id(
        "MTPL_FREQ",
        "scheduled__2026-04-27T10:30:00+00:00",
    )

    assert export_id == "mtpl_freq__scheduled__20260427t1030000000"


def test_export_rating_tables_forwards_weights_and_offset(tmp_path: Path):
    model = _ExportModel()
    output_path = tmp_path / "nested" / "rating_tables.xlsx"
    X = pd.DataFrame({"x": [1, 2]})
    y = np.array([0.0, 1.0])
    export_weight = np.array([0.5, 2.0])
    offset = np.log(np.array([1.0, 3.0]))
    offset_source = pd.Series([12, 36], name="TermMonths")

    result = rating_tables.export_rating_tables(
        model,
        X,
        y,
        export_weight,
        output_path,
        offset=offset,
        offset_source=offset_source,
        offset_name="TermMonths",
        offset_kind="discrete",
        offset_max_exact_levels=50,
    )

    assert result == output_path
    assert output_path.read_bytes() == b"workbook"
    args, kwargs = model.calls[0]
    assert args == (output_path, X, y)
    np.testing.assert_array_equal(kwargs.pop("sample_weight"), export_weight)
    np.testing.assert_array_equal(kwargs.pop("offset"), offset)
    pd.testing.assert_series_equal(kwargs.pop("offset_source"), offset_source)
    assert kwargs == {
        "n_bins": 150,
        "offset_name": "TermMonths",
        "offset_kind": "discrete",
        "offset_max_exact_levels": 50,
    }


def test_export_rating_tables_preserves_raw_offset_levels(tmp_path: Path):
    from superglm import Categorical, SuperGLM

    row_count = 80
    term = pd.Series(np.resize([12.0, 36.0], row_count), name="Term")
    X = pd.DataFrame({"territory": np.resize(["north", "south"], row_count)})
    offset = np.log(term / 12.0)
    y = np.random.default_rng(20260716).poisson(np.exp(-1.0 + offset.to_numpy()))
    model = SuperGLM(
        features={"territory": Categorical(base="first")},
        selection_penalty=0.0,
    ).fit(X, y, offset=offset)
    workbook_path = tmp_path / "rating_tables.xlsx"

    rating_tables.export_rating_tables(
        model,
        X,
        y,
        np.ones(row_count),
        workbook_path,
        offset=offset,
        offset_source=term,
        offset_name="Term",
        offset_kind="discrete",
    )

    raw = pd.read_excel(workbook_path, sheet_name="Rating Tables", header=None)
    header_positions = [
        (row, column)
        for row in range(len(raw))
        for column in range(len(raw.columns) - 1)
        if raw.iat[row, column] == "Term" and raw.iat[row, column + 1] == "Relativity"
    ]
    assert len(header_positions) == 1
    header_row, source_column = header_positions[0]
    offset_rows = raw.iloc[header_row + 1 :, [source_column, source_column + 1]].dropna()
    relativities = dict(
        zip(
            pd.to_numeric(offset_rows.iloc[:, 0]),
            pd.to_numeric(offset_rows.iloc[:, 1]),
            strict=True,
        )
    )

    assert relativities == pytest.approx({12.0: 1.0, 36.0: 3.0})


def test_export_rating_tables_requires_supported_superglm(tmp_path: Path):
    with pytest.raises(RuntimeError, match=r"SuperGLM.*export_rating_tables"):
        rating_tables.export_rating_tables(
            object(),
            pd.DataFrame({"x": [1]}),
            np.array([0.0]),
            np.array([1.0]),
            tmp_path / "rating_tables.xlsx",
        )


def _offline_staging_engine(tmp_path: Path):
    engine = sqlite_engine_with_offline_schemas(
        {
            "pricing": tmp_path / "pricing.sqlite",
            "pricing_stg": tmp_path / "pricing_stg.sqlite",
            "mlops": tmp_path / "mlops.sqlite",
        }
    )
    apply_offline_ddl(engine)
    return engine


def _minimal_rating_workbook(
    path: Path,
    *,
    term_name: str = "TermMonths",
    level_code: str = "12",
) -> Path:
    raw = pd.DataFrame([[None] * 3 for _ in range(8)])
    raw.iat[1, 2] = 0.123
    raw.iat[4, 0] = term_name
    raw.iloc[6, 0:3] = [term_name, "Relativity", "Weight"]
    raw.iloc[7, 0:3] = [level_code, 1.0, 10.0]
    raw.to_excel(path, sheet_name="Rating Tables", header=False, index=False)
    return path


def _publication_receipt(
    *,
    handling: str = "EXPORTED_FACTOR",
    published_factor_name: str | None = "TermMonths",
    term_metadata: dict[str, dict[str, object]] | None = None,
) -> SuperGLMPublicationReceipt:
    if handling == "EXPORTED_FACTOR":
        offset_contract = OffsetExportContract(
            handling="EXPORTED_FACTOR",
            source_factor_name="term_months",
            published_factor_name=published_factor_name,
            source_name="Exposure",
            label="Policy exposure term",
        )
        default_term_metadata = {
            "TermMonths": {
                "feature_kind": "offset",
                "source_column": "Exposure",
            }
        }
    else:
        offset_contract = OffsetExportContract(handling="NONE")
        default_term_metadata = {}

    return SuperGLMPublicationReceipt(
        schema_name="superglm_publication_receipt",
        schema_version=1,
        metadata_origin="SUPERGLM_FITTED_MODEL",
        superglm_version="1.0.0",
        extractor_version="unit-test",
        package_metadata={"model": {"family": "poisson", "link": "log"}},
        term_metadata=term_metadata if term_metadata is not None else default_term_metadata,
        offset_contract=offset_contract,
    )


def test_prepared_rating_tables_are_backend_neutral(tmp_path: Path):
    workbook = _minimal_rating_workbook(tmp_path / "rating_tables.xlsx")
    receipt_path = tmp_path / "publication_receipt.json"
    receipt_sha256 = write_publication_receipt(_publication_receipt(), receipt_path)
    build = ApprovedModelBuild.model_construct(
        model_id=1,
        model_name=MODEL_CONFIG.model_name,
        model_version="v1",
        target_name=MODEL_CONFIG.target_name,
        model_type=MODEL_CONFIG.model_type,
        export_id="export-1",
        effective_from=None,
        created_by="analyst@example.test",
        publication_receipt_path=str(receipt_path),
        publication_receipt_sha256=receipt_sha256,
        model_equivalence_sha256=None,
    )
    tables = prepare_rating_tables(
        workbook_path=workbook,
        build=build,
        model_config=MODEL_CONFIG,
        effective_to=None,
    )

    assert isinstance(tables, RatingTables)
    assert list(tables.export_frame["export_id"]) == [build.export_id]
    assert not tables.rate_cells.empty
    assert not tables.cell_levels.empty
    assert re.fullmatch(r"[0-9a-f]{64}", tables.staging_content_sha256)
    assert re.fullmatch(r"[0-9a-f]{64}", tables.model_equivalence_sha256)


def test_build_staging_frames_accepts_mapping_and_uses_standard_layout(tmp_path: Path):
    workbook_path = _minimal_rating_workbook(tmp_path / "rating_tables.xlsx")
    args = rating_tables.StagingExport(
        workbook_path=workbook_path,
        export_id="export-1",
        model_name="MTPL_FREQ",
        model_version="v1",
        effective_from=None,
        effective_to=None,
        interaction_features=MappingProxyType({}),
        created_by="analyst@example.test",
    )

    export, rates, _levels = rating_tables.build_staging_frames(args)

    assert export.iloc[0]["base_rate"] == pytest.approx(0.123)
    assert export.iloc[0]["source_file"] == str(workbook_path.resolve())
    assert rates.iloc[0]["term_name"] == "TermMonths"


def test_stage_rating_export_persists_receipt_offset_and_content_digest(tmp_path: Path):
    engine = _offline_staging_engine(tmp_path)
    workbook_path = _minimal_rating_workbook(tmp_path / "rating_tables.xlsx")
    receipt_path = tmp_path / "publication_receipt.json"
    receipt_sha256 = write_publication_receipt(_publication_receipt(), receipt_path)

    build = ApprovedModelBuild.model_construct(
        model_id=1,
        model_name=MODEL_CONFIG.model_name,
        target_name=MODEL_CONFIG.target_name,
        model_type=MODEL_CONFIG.model_type,
        created_by="python",
        export_id="export-1",
        model_version="20260427",
        effective_from=None,
        publication_receipt_path=str(receipt_path),
        publication_receipt_sha256=receipt_sha256,
    )
    tables = prepare_rating_tables(
        workbook_path=workbook_path,
        build=build,
        model_config=MODEL_CONFIG,
        effective_to=None,
    )
    prepared = publication.prepare_publication(
        publication.PublicationRequest(
            build=build,
            model_config=MODEL_CONFIG,
            execution_name="test",
            execution_id=build.export_id,
            allowed_artifact_root=None,
        )
    )
    with engine.begin() as connection:
        sqlserver._replace_staging_frames(connection, prepared, tables)
    content_sha256 = tables.staging_content_sha256

    with engine.begin() as connection:
        export = (
            connection.execute(
                text(
                    "SELECT publication_receipt_sha256, offset_handling, "
                    "offset_factor_name, staging_content_sha256, "
                    "model_equivalence_sha256 "
                    "FROM pricing_stg.STG_RATING_EXPORT WHERE export_id = :export_id"
                ),
                {"export_id": "export-1"},
            )
            .mappings()
            .one()
        )
        term = (
            connection.execute(
                text(
                    "SELECT term_type FROM pricing_stg.STG_RATE_CELL "
                    "WHERE export_id = :export_id AND term_name = :term_name"
                ),
                {"export_id": "export-1", "term_name": "TermMonths"},
            )
            .mappings()
            .one()
        )
        metadata_json = connection.execute(
            text(
                "SELECT term_metadata_json FROM pricing_stg.STG_TERM_METADATA "
                "WHERE export_id = :export_id AND term_name = :term_name"
            ),
            {"export_id": "export-1", "term_name": "TermMonths"},
        ).scalar_one()

    assert len(content_sha256) == 64
    assert export["publication_receipt_sha256"] == receipt_sha256
    assert export["staging_content_sha256"] == content_sha256
    assert len(export["model_equivalence_sha256"]) == 64
    assert export["offset_handling"] == "EXPORTED_FACTOR"
    assert export["offset_factor_name"] == "TermMonths"
    assert term["term_type"] == "OFFSET_FACTOR"
    assert json.loads(metadata_json)["feature_kind"] == "offset"


def test_stage_rating_export_requires_publication_receipt(tmp_path: Path):
    workbook_path = _minimal_rating_workbook(tmp_path / "rating_tables.xlsx")
    with pytest.raises(TypeError, match="publication_receipt"):
        rating_tables.rating_workbook_model_equivalence_sha256(
            workbook_path=workbook_path,
            export_id="export-1",
            model_name="MTPL_FREQ",
            model_version="v1",
            effective_from=None,
        )


def test_stage_rating_export_rejects_receipt_term_missing_from_workbook(tmp_path: Path):
    workbook_path = _minimal_rating_workbook(
        tmp_path / "rating_tables.xlsx",
        term_name="LogDensity",
        level_code="per_unit",
    )
    receipt_path = tmp_path / "publication_receipt.json"
    receipt_sha256 = write_publication_receipt(
        _publication_receipt(
            handling="NONE",
            term_metadata={
                "LogDensity": {"feature_kind": "numeric"},
                "MissingTerm": {"feature_kind": "categorical"},
            },
        ),
        receipt_path,
    )

    with pytest.raises(ValueError, match="not present in staged workbook"):
        rating_tables.rating_workbook_model_equivalence_sha256(
            workbook_path=workbook_path,
            export_id="export-1",
            model_name="MTPL_FREQ",
            model_version="v1",
            effective_from=None,
            publication_receipt_path=receipt_path,
            publication_receipt_sha256=receipt_sha256,
        )


def test_staging_content_sha256_binds_every_frame():
    export = pd.DataFrame([{"export_id": "export-1", "model_name": "MTPL_FREQ"}])
    rates = pd.DataFrame(
        [{"export_id": "export-1", "row_id": 1, "term_name": "Area", "multiplier": 1.1}]
    )
    levels = pd.DataFrame(
        [{"export_id": "export-1", "row_id": 1, "position_no": 1, "level_code": "A"}]
    )
    terms = pd.DataFrame(
        [
            {
                "export_id": "export-1",
                "term_name": "Area",
                "term_metadata_json": '{"feature_kind":"categorical"}',
            }
        ]
    )
    digest = rating_tables.staging_content_sha256(export, rates, levels, terms)

    changed_rates = rates.copy()
    changed_rates.loc[0, "multiplier"] = 1.2
    changed_levels = levels.copy()
    changed_levels.loc[0, "level_code"] = "B"
    changed_terms = terms.copy()
    changed_terms.loc[0, "term_metadata_json"] = '{"feature_kind":"numeric"}'

    assert len(digest) == 64
    assert rating_tables.staging_content_sha256(export, changed_rates, levels, terms) != digest
    assert rating_tables.staging_content_sha256(export, rates, changed_levels, terms) != digest
    assert rating_tables.staging_content_sha256(export, rates, levels, changed_terms) != digest


def test_model_equivalence_ignores_volatile_identity_and_uses_small_numeric_tolerance():
    export = pd.DataFrame(
        [
            {
                "export_id": "export-1",
                "model_id": 17,
                "model_name": "MTPL_FREQ",
                "model_version": "v1",
                "base_rate": 0.123456789001,
                "source_file": "/first/rating.xlsx",
                "package_metadata_json": '{"family":"poisson","link":"log"}',
            }
        ]
    )
    rates = pd.DataFrame(
        [
            {
                "export_id": "export-1",
                "row_id": 1,
                "sequence_no": 1,
                "term_name": "Area",
                "term_type": "CATEGORICAL_MAIN",
                "cell_key_text": "Area=A",
                "multiplier": 1.234567890001,
                "log_coefficient": np.log(1.234567890001),
            }
        ]
    )
    levels = pd.DataFrame(
        [
            {
                "export_id": "export-1",
                "row_id": 1,
                "position_no": 1,
                "feature_name": "Area",
                "level_set_name": "Area__export-1",
                "level_code": "A",
                "order_index": 1,
            }
        ]
    )
    terms = pd.DataFrame(
        [
            {
                "export_id": "export-1",
                "term_name": "Area",
                "term_metadata_json": '{"published_term_name":"Area","feature_kind":"categorical"}',
            }
        ]
    )
    digest = rating_tables.model_equivalence_sha256(export, rates, levels, terms)

    retry_export = export.assign(
        export_id="export-2",
        model_version="v2",
        source_file="/second/rating.xlsx",
        base_rate=0.123456789002,
    )
    retry_rates = rates.assign(
        export_id="export-2",
        row_id=99,
        sequence_no=8,
        multiplier=1.234567890002,
        log_coefficient=np.log(1.234567890002),
    )
    retry_levels = levels.assign(
        export_id="export-2",
        row_id=99,
        level_set_name="Area__export-2",
        order_index=12,
    )
    retry_terms = terms.assign(export_id="export-2")

    assert (
        rating_tables.model_equivalence_sha256(
            retry_export,
            retry_rates,
            retry_levels,
            retry_terms,
        )
        == digest
    )

    materially_changed = retry_rates.copy()
    materially_changed.loc[0, "multiplier"] = 1.23456799
    materially_changed.loc[0, "log_coefficient"] = np.log(1.23456799)
    assert (
        rating_tables.model_equivalence_sha256(
            retry_export,
            materially_changed,
            retry_levels,
            retry_terms,
        )
        != digest
    )

    changed_level = retry_levels.copy()
    changed_level.loc[0, "level_code"] = "B"
    assert (
        rating_tables.model_equivalence_sha256(
            retry_export,
            retry_rates,
            changed_level,
            retry_terms,
        )
        != digest
    )


def test_workbook_equivalence_is_calculated_entirely_in_python_before_staging(
    tmp_path: Path,
):
    workbook_path = _minimal_rating_workbook(tmp_path / "rating_tables.xlsx")
    receipt_path = tmp_path / "publication_receipt.json"
    receipt_sha256 = write_publication_receipt(_publication_receipt(), receipt_path)

    first = rating_tables.rating_workbook_model_equivalence_sha256(
        workbook_path=workbook_path,
        export_id="export-1",
        model_name="MTPL_FREQ",
        model_version="v1",
        effective_from="2026-08-01",
        publication_receipt_path=receipt_path,
        publication_receipt_sha256=receipt_sha256,
    )
    retry = rating_tables.rating_workbook_model_equivalence_sha256(
        workbook_path=workbook_path,
        export_id="export-2",
        model_name="MTPL_FREQ",
        model_version="v2",
        effective_from="2026-09-01",
        publication_receipt_path=receipt_path,
        publication_receipt_sha256=receipt_sha256,
    )

    assert first == retry


def test_stage_rating_export_parses_categorical_interaction_matrix(
    tmp_path: Path,
):
    from superglm import Categorical, SuperGLM

    from pricing_pipeline.publishing.metadata import (
        build_superglm_publication_receipt,
    )

    n_rows = 60
    X = pd.DataFrame(
        {
            "territory": np.resize(["urban", "rural"], n_rows),
            "age_band": np.resize(["young", "old", "mid"], n_rows),
        }
    )
    y = np.random.default_rng(20260713).poisson(0.4, size=n_rows)
    weights = np.ones(n_rows)
    model = SuperGLM(
        features={
            "territory": Categorical(base="first"),
            "age_band": Categorical(base="first"),
        },
        interactions=[("territory", "age_band")],
        selection_penalty=0.0,
    ).fit(X, y, sample_weight=weights)
    workbook_path = tmp_path / "rating_tables.xlsx"
    rating_tables.export_rating_tables(
        model,
        X,
        y,
        weights,
        workbook_path,
    )
    receipt_path = tmp_path / "publication_receipt.json"
    receipt_sha256 = write_publication_receipt(
        build_superglm_publication_receipt(
            model,
            offset_contract=OffsetExportContract(handling="NONE"),
        ),
        receipt_path,
    )
    build = ApprovedModelBuild.model_construct(
        model_id=17,
        model_name=MODEL_CONFIG.model_name,
        model_version="v1",
        target_name=MODEL_CONFIG.target_name,
        model_type=MODEL_CONFIG.model_type,
        export_id="export-1",
        effective_from=None,
        created_by="python",
        publication_receipt_path=str(receipt_path),
        publication_receipt_sha256=receipt_sha256,
    )
    tables = prepare_rating_tables(
        workbook_path=workbook_path,
        build=build,
        model_config=MODEL_CONFIG,
        effective_to=None,
    )

    interactions = tables.rate_cells.query("term_name == 'territory_age_band'")
    interaction_levels = tables.cell_levels.loc[
        tables.cell_levels["row_id"].isin(interactions["row_id"])
    ]
    assert len(interactions) == 6
    assert set(interactions["term_type"]) == {"CATEGORICAL_INTERACTION"}
    assert len(interaction_levels) == 12
    assert set(interaction_levels["position_no"]) == {1, 2}
    assert set(tables.term_metadata["term_name"]) == {
        "territory",
        "age_band",
        "territory_age_band",
    }


class _Result:
    def __init__(self, *, row=None, rows=(), scalar=None):
        self.row = row
        self.rows = list(rows)
        self.scalar = scalar

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row

    def all(self):
        return self.rows

    def scalar_one(self):
        return self.scalar

    def scalar_one_or_none(self):
        return self.scalar


class _LineageConnection:
    def __init__(self, *, existing=None, associations=()):
        self.existing = existing
        self.associations = list(associations)
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))
        if "FROM pricing.MODEL_RUN AS mr" in sql:
            return _Result(row=self.existing)
        if "lineage_source" in sql:
            return _Result(rows=self.associations)
        if "child_package.parent_rate_package_id" in sql:
            return _Result(scalar=1)
        if "SELECT model_run_id" in sql:
            return _Result(scalar=501)
        return _Result()


class _Begin:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, tb):
        return False


class _Engine:
    def __init__(self, connection):
        self.connection = connection

    def begin(self):
        return _Begin(self.connection)


def _model_run_build(**overrides):
    values = {
        "model_id": 17,
        "model_name": "MTPL_FREQ",
        "model_version": "v1",
        "model_type": "superglm_poisson",
        "target_name": "ClaimNb",
        "deployment_slot": "MTPL_FREQ_UAT",
        "manifest_id": "manifest-1",
        "split_set_id": "split-1",
        "export_id": "export-1",
        "rating_workbook_path": "/tmp/rating.xlsx",
        "rating_workbook_sha256": "f" * 64,
        "created_by": "analyst@example.test",
        "mlflow_run_id": None,
        "publication_receipt_path": "/tmp/publication_receipt.json",
        "publication_receipt_sha256": "c" * 64,
        "candidate_artifact_path": "/tmp/candidate.joblib",
        "candidate_artifact_sha256": "a" * 64,
        "candidate_artifact_format": "superglm-candidate-joblib-v2",
        "candidate_artifact_size_bytes": 123,
        "candidate_python_version": "3.14.4",
        "candidate_superglm_version": "0.11.0",
        "model_source_sha256": "b" * 64,
        "model_frame_sha256": "d" * 64,
    }
    values.update(overrides)
    return ModelExportResult(**values)


def _model_run_kwargs():
    return {
        "build": _model_run_build(),
        "dag_id": "pricing.model.build",
        "airflow_run_id": "notebook__2026-07-12",
        "rate_package_id": 42,
        "parent_model_run_id": 409,
    }


def test_record_model_run_writes_identity_associations_parent_and_metrics():
    connection = _LineageConnection()
    kwargs = _model_run_kwargs()
    kwargs["build"] = _model_run_build(
        metrics={"deviance": 0.42},
        metric_scopes={"deviance": "cv"},
        fold_metrics=({"fold_no": 1, "metric_name": "deviance", "metric_value": 0.4},),
    )

    model_run_id = lineage.record_model_run(
        _Engine(connection),
        **kwargs,
    )

    assert model_run_id == 501
    model_run_write = next(
        item for item in connection.statements if "INSERT INTO pricing.MODEL_RUN" in item[0]
    )
    assert model_run_write[1]["candidate_artifact_sha256"] == "a" * 64
    assert model_run_write[1]["model_source_sha256"] == "b" * 64
    assert model_run_write[1]["parent_model_run_id"] == 409
    assert any("INSERT INTO mlops.MODEL_RUN_DATASET" in sql for sql, _ in connection.statements)
    assert any("INSERT INTO mlops.MODEL_RUN_SPLIT_SET" in sql for sql, _ in connection.statements)
    assert any("INSERT INTO mlops.MODEL_RUN_METRIC" in sql for sql, _ in connection.statements)
    assert any("INSERT INTO pricing.CV_FOLD_METRIC" in sql for sql, _ in connection.statements)
    assert any(
        "parent.model_run_id = :parent_model_run_id" in sql for sql, _ in connection.statements
    )


_RETRY_ARTIFACTS = {}


def _retry_artifact_fields(tmp_path: Path):
    key = tmp_path.resolve()
    if key not in _RETRY_ARTIFACTS:
        receipt = tmp_path / "publication_receipt.json"
        receipt.write_bytes(b"publication receipt")
        metadata = save_candidate_bundle(
            CandidateBundle(
                fitted_model=SimpleNamespace(name="candidate"),
                X=pd.DataFrame({"age": [42.0]}),
                y=np.zeros(1),
                sample_weight=None,
                offset=None,
                export_weight=None,
                cv_report={},
                model_name="MTPL_FREQ",
                model_version="v1",
                export_id="export-1",
                manifest_id="manifest-1",
                split_set_id="split-1",
                pk_columns=("policy_id",),
                row_order_sha256="d" * 64,
                model_source_sha256="c" * 64,
                model_frame_sha256="e" * 64,
                offset_contract={"handling": "NONE"},
            ),
            tmp_path / "candidate.joblib",
        )
        _RETRY_ARTIFACTS[key] = {
            "publication_receipt_path": str(receipt),
            "publication_receipt_sha256": pipeline.sha256_file(receipt),
            "candidate_artifact_path": str(metadata.path),
            "candidate_artifact_sha256": metadata.sha256,
            "candidate_artifact_format": metadata.format,
            "candidate_artifact_size_bytes": metadata.size_bytes,
            "candidate_python_version": metadata.python_version,
            "candidate_superglm_version": metadata.superglm_version,
            "model_source_sha256": "c" * 64,
            "model_frame_sha256": "e" * 64,
        }
    return _RETRY_ARTIFACTS[key]


def _retry_export(tmp_path: Path) -> ModelExportResult:
    workbook_path = (tmp_path / "rating_tables.xlsx").resolve()
    if not workbook_path.exists():
        workbook_path.write_bytes(b"rating workbook")
    return ModelExportResult(
        model_id=17,
        model_name="MTPL_FREQ",
        model_version="v1",
        model_type="superglm_poisson",
        target_name="ClaimNb",
        deployment_slot="MTPL_FREQ_UAT",
        manifest_id="manifest-1",
        mlflow_run_id=None,
        split_set_id="split-1",
        export_id="export-1",
        rating_workbook_path=str(workbook_path),
        rating_workbook_sha256=pipeline.sha256_file(workbook_path),
        effective_from=None,
        created_by="analyst@example.test",
        metrics={"deviance": 0.42},
        metric_scopes={"deviance": "cv"},
        fold_metrics=({"fold_no": 1, "metric_name": "deviance", "metric_value": 0.4},),
        **_retry_artifact_fields(tmp_path),
    )


def _retry_evidence(tmp_path: Path):
    workbook = (tmp_path / "rating_tables.xlsx").resolve()
    if not workbook.exists():
        workbook.write_bytes(b"rating workbook")
    workbook_path = str(workbook)
    workbook_sha256 = pipeline.sha256_file(workbook)
    artifacts = _retry_artifact_fields(tmp_path)
    return {
        "row": {
            "model_id": 17,
            "model_name": "MTPL_FREQ",
            "model_version": "v1",
            "source_export_id": "export-1",
            "rate_package_id": 42,
            "package_version": 3,
            "package_status": "PUBLISHED",
            "parent_rate_package_id": None,
            "effective_from_date": None,
            "effective_to_date": None,
            "source_file": workbook_path,
            "package_publication_receipt_sha256": artifacts["publication_receipt_sha256"],
            "model_run_id": 501,
            "run_status": "SUCCESS",
            "run_export_id": "export-1",
            "run_model_id": 17,
            "run_model_name": "MTPL_FREQ",
            "run_model_version": "v1",
            "dag_id": "notebook",
            "airflow_run_id": "export-1",
            "manifest_id": "manifest-1",
            "rating_workbook_path": workbook_path,
            "rating_workbook_sha256": workbook_sha256,
            "mlflow_run_id": None,
            **artifacts,
        },
        "datasets": [{"manifest_id": "manifest-1", "dataset_role": "training"}],
        "splits": [
            {
                "manifest_id": "manifest-1",
                "split_set_id": "split-1",
                "dataset_role": "training",
                "split_role": "validation",
            }
        ],
        "metrics": [{"metric_name": "deviance", "metric_value": 0.42, "metric_scope": "cv"}],
        "folds": [
            {
                "split_set_id": "split-1",
                "fold_no": 1,
                "metric_name": "deviance",
                "metric_value": 0.4,
            }
        ],
    }


class _EvidenceConnection:
    def __init__(self, evidence):
        self.evidence = evidence

    def execute(self, statement, params):
        sql = str(statement)
        if "FROM pricing.PRICING_RATE_PACKAGE AS rp" in sql:
            return _Result(rows=[self.evidence["row"]])
        if "FROM mlops.MODEL_RUN_DATASET" in sql:
            return _Result(rows=self.evidence["datasets"])
        if "FROM mlops.MODEL_RUN_SPLIT_SET" in sql:
            return _Result(rows=self.evidence["splits"])
        if "FROM mlops.MODEL_RUN_METRIC" in sql:
            return _Result(rows=self.evidence["metrics"])
        if "FROM pricing.CV_FOLD_METRIC" in sql:
            return _Result(rows=self.evidence["folds"])
        raise AssertionError(f"unexpected evidence query: {sql}")


def test_existing_published_run_requires_exact_complete_evidence(tmp_path: Path):
    export = _retry_export(tmp_path)
    evidence = _retry_evidence(tmp_path)

    result = pipeline._resolve_existing_published_run(
        _Engine(_EvidenceConnection(evidence)),
        export,
        allowed_artifact_root=tmp_path,
    )

    assert result == CompletedModelPublishResult(
        model_id=17,
        model_name="MTPL_FREQ",
        model_version="v1",
        manifest_id="manifest-1",
        split_set_id="split-1",
        export_id="export-1",
        rate_package_id=42,
        package_version=3,
        package_status="PUBLISHED",
        rating_workbook_path=export.rating_workbook_path,
        model_run_id=501,
        mlflow_run_id=None,
        publication_receipt_path=export.publication_receipt_path,
        publication_receipt_sha256=export.publication_receipt_sha256,
        was_existing=True,
    )

    evidence["row"]["model_run_id"] = None
    with pytest.raises(pipeline.PublishedRunIntegrityError, match="manual repair"):
        pipeline._resolve_existing_published_run(
            _Engine(_EvidenceConnection(evidence)),
            export,
            allowed_artifact_root=tmp_path,
        )


@pytest.mark.parametrize(
    ("mutation", "field_name"),
    [
        (lambda evidence: evidence["row"].update(dag_id="other"), "dag_id"),
        (
            lambda evidence: evidence["datasets"].append(
                {"manifest_id": "extra", "dataset_role": "training"}
            ),
            "dataset links",
        ),
        (
            lambda evidence: evidence["splits"][0].update(split_set_id="other"),
            "split links",
        ),
        (
            lambda evidence: evidence["metrics"][0].update(metric_value=9.0),
            "metrics",
        ),
    ],
)
def test_existing_published_run_rejects_conflicting_evidence(
    tmp_path: Path,
    mutation,
    field_name,
):
    evidence = deepcopy(_retry_evidence(tmp_path))
    mutation(evidence)

    with pytest.raises(
        pipeline.PublishedRunIntegrityError,
        match=rf"incompatible evidence.*{field_name}",
    ):
        pipeline._resolve_existing_published_run(
            _Engine(_EvidenceConnection(evidence)),
            _retry_export(tmp_path),
            allowed_artifact_root=tmp_path,
        )


def test_existing_published_run_verifies_candidate_bundle_identity(tmp_path: Path):
    evidence = _retry_evidence(tmp_path)
    metadata = save_candidate_bundle(
        CandidateBundle(
            fitted_model=SimpleNamespace(name="candidate"),
            X=pd.DataFrame({"age": [42.0]}),
            y=np.zeros(1),
            sample_weight=None,
            offset=None,
            export_weight=None,
            cv_report={},
            model_name="MTPL_FREQ",
            model_version="v1",
            export_id="export-1",
            manifest_id="manifest-1",
            split_set_id="split-1",
            pk_columns=("policy_id",),
            row_order_sha256="d" * 64,
            model_source_sha256="b" * 64,
            model_frame_sha256="e" * 64,
            offset_contract={"handling": "NONE"},
        ),
        tmp_path / "candidate.joblib",
    )
    artifact_fields = {
        "candidate_artifact_path": metadata.path,
        "candidate_artifact_sha256": metadata.sha256,
        "candidate_artifact_format": metadata.format,
        "candidate_artifact_size_bytes": metadata.size_bytes,
        "candidate_python_version": metadata.python_version,
        "candidate_superglm_version": metadata.superglm_version,
        "model_source_sha256": "c" * 64,
    }
    evidence["row"].update(artifact_fields)
    export = ModelExportResult(**{**_retry_export(tmp_path).model_dump(), **artifact_fields})

    with pytest.raises(
        pipeline.PublishedRunIntegrityError,
        match="candidate artifact source hash does not match model-run lineage",
    ):
        pipeline._resolve_existing_published_run(
            _Engine(_EvidenceConnection(evidence)),
            export,
            allowed_artifact_root=tmp_path,
        )


def test_publish_model_export_stages_packages_and_records_lineage(
    monkeypatch,
    tmp_path: Path,
):
    calls = []
    export = _retry_export(tmp_path)
    tables = SimpleNamespace(model_equivalence_sha256="f" * 64)
    monkeypatch.setattr(
        publication,
        "prepare_rating_tables",
        lambda **kwargs: calls.append(("prepare", kwargs)) or tables,
    )

    def publish(engine, prepared, prepared_tables):
        calls.append(("publish", engine, prepared, prepared_tables))
        return CompletedModelPublishResult(
            model_id=17,
            model_name=export.model_name,
            model_version=export.model_version,
            manifest_id=export.manifest_id,
            split_set_id=export.split_set_id,
            mlflow_run_id="",
            export_id="export-1",
            rate_package_id=42,
            package_version=3,
            package_status="PUBLISHED",
            rating_workbook_path="",
            model_run_id=501,
            model_equivalence_sha256="f" * 64,
        )

    monkeypatch.setattr(sqlserver, "publish_sqlserver", publish)

    result = pipeline.publish_model_export(
        object(),
        export,
        model_config=MODEL_CONFIG,
        validated_model_id=17,
    )

    assert isinstance(result, CompletedModelPublishResult)
    assert result.rate_package_id == 42
    assert result.model_run_id == 501
    assert result.was_existing is False
    prepare_call = next(call for call in calls if call[0] == "prepare")
    assert prepare_call[1]["workbook_path"] == Path(export.rating_workbook_path)
    assert prepare_call[1]["build"] is export
    publish_call = next(call for call in calls if call[0] == "publish")
    assert publish_call[2].build.model_equivalence_sha256 == "f" * 64
    assert publish_call[3] is tables


def test_publish_model_export_returns_verified_existing_result_without_rewriting_lineage(
    monkeypatch,
    tmp_path: Path,
):
    export = _retry_export(tmp_path)
    tables = SimpleNamespace(model_equivalence_sha256="f" * 64)
    existing = CompletedModelPublishResult(
        model_id=17,
        model_name="MTPL_FREQ",
        model_version="v1",
        manifest_id="manifest-1",
        split_set_id="split-1",
        export_id="export-1",
        rate_package_id=42,
        package_version=3,
        package_status="PUBLISHED",
        rating_workbook_path=export.rating_workbook_path,
        model_run_id=501,
        was_existing=True,
    )
    monkeypatch.setattr(
        publication,
        "prepare_rating_tables",
        lambda **kwargs: tables,
    )
    monkeypatch.setattr(
        sqlserver,
        "publish_sqlserver",
        lambda engine, prepared, prepared_tables: existing,
    )

    result = pipeline.publish_model_export(
        object(),
        export,
        model_config=MODEL_CONFIG,
        validated_model_id=17,
    )

    assert result is existing


def test_publish_model_export_reuses_equivalent_run_before_any_staging_write(
    monkeypatch,
    tmp_path: Path,
):
    export = _retry_export(tmp_path)
    tables = SimpleNamespace(model_equivalence_sha256="f" * 64)
    equivalent = SimpleNamespace(
        model_id=17,
        model_name="MTPL_FREQ",
        model_version="v1",
        export_id="export-original",
        manifest_id="manifest-1",
        split_set_id="split-1",
        rate_package_id=42,
        package_version=3,
        package_status="PUBLISHED",
        rating_workbook_path="/durable/original.xlsx",
        model_run_id=501,
        mlflow_run_id=None,
        publication_receipt_path="/durable/original-receipt.json",
        publication_receipt_sha256="9" * 64,
        model_kind="RAW",
        model_equivalence_sha256="f" * 64,
    )
    calls = []
    monkeypatch.setattr(
        publication,
        "prepare_rating_tables",
        lambda **kwargs: calls.append("prepare") or tables,
    )
    monkeypatch.setattr(
        sqlserver,
        "publish_sqlserver",
        lambda engine, prepared, prepared_tables: (
            calls.append("publish")
            or CompletedModelPublishResult(
                model_id=equivalent.model_id,
                model_name=equivalent.model_name,
                model_version=equivalent.model_version,
                manifest_id=equivalent.manifest_id,
                split_set_id=equivalent.split_set_id,
                export_id=equivalent.export_id,
                rate_package_id=equivalent.rate_package_id,
                package_version=equivalent.package_version,
                package_status=equivalent.package_status,
                rating_workbook_path=equivalent.rating_workbook_path,
                model_run_id=equivalent.model_run_id,
                publication_receipt_path=equivalent.publication_receipt_path,
                publication_receipt_sha256=equivalent.publication_receipt_sha256,
                was_existing=True,
                deduplicated=True,
                model_kind=equivalent.model_kind,
                model_equivalence_sha256=equivalent.model_equivalence_sha256,
            )
        ),
    )

    result = pipeline.publish_model_export(
        object(),
        export,
        model_config=MODEL_CONFIG,
        validated_model_id=17,
    )

    assert calls == ["prepare", "publish"]
    assert result.rate_package_id == 42
    assert result.export_id == "export-original"
    assert result.was_existing is True
    assert result.deduplicated is True
    assert result.model_equivalence_sha256 == "f" * 64
