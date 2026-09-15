"""Run the recurring batch against a deployed SQLite publication."""

import json
import logging
import shutil
from dataclasses import fields, replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text
from superglm import SuperGLM

from pricing_pipeline import notebook as api
from pricing_pipeline.data.manifest import model_frame_evidence
from pricing_pipeline.modeling.monitoring import MonitoringDataError, MonitoringError
from tests.recipes.test_monitoring_baseline_sql import _deploy


def _fresh_dataset(*, weighted=False):
    rng = np.random.default_rng(108)
    rows = 240
    df = pd.DataFrame(
        {
            "id": np.arange(rows) + 10_000,
            "monitor_as_of": "2026-09-15",
            "region": np.resize(["A"] * 6 + ["B", "C"], rows),
            "bonus_malus": np.resize(["0", "1", "2", "3", "4", "Unknown"], rows),
            "x": rng.uniform(0.2, 4.8, rows),
            "z": rng.normal(size=rows),
            "exposure": rng.uniform(0.5, 1.5, rows),
        }
    )
    df["claim_count"] = rng.poisson(df.exposure * np.exp(0.9 + 0.1 * df.x))
    if weighted:
        df["fit_weight"] = np.where(df.region.eq("A"), 2.0, 1.0)
        df["rating_weight"] = rng.uniform(1.0, 3.0, rows)
    # Column order and index are deliberately unrelated to the original fit.
    df = df.loc[:, list(reversed(df.columns))]
    df.index = np.arange(rows) + 20_000
    return api.PricingDataset(
        df, name="current_claims", source="current SQL query", key="id", as_of="monitor_as_of"
    )


def _published_baseline(pricing, model, candidate):
    saved = api.save_model_version(pricing, candidate)
    _deploy(pricing, saved)
    build = candidate.completed_build
    for filename in (
        build.candidate_artifact_path,
        build.rating_workbook_path,
        build.publication_receipt_path,
    ):
        Path(filename).unlink()
    shutil.rmtree(model.source_root)
    return api.load_monitoring_baseline(pricing, model=model), saved


def _sql_count(engine, table):
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT COUNT(*) FROM pricing.{table}")).scalar_one()


def test_batch_persists_four_variants_without_local_baseline_files(fitted_case, caplog):
    from pricing_pipeline.modeling.monitoring.batch import MonitoringReport, run_monitoring_batch

    pricing, model, candidate, _ = fitted_case
    baseline, saved = _published_baseline(pricing, model, candidate)
    dataset = _fresh_dataset()
    before = dataset.df
    with caplog.at_level(logging.INFO, logger="pricing_pipeline.monitoring"):
        report = run_monitoring_batch(
            pricing.engine,
            baseline,
            dataset,
            target_column="claim_count",
            component_role="FREQUENCY",
            created_by="scheduled-test",
            continuous_points=9,
            max_reml_iter=3,
        )

    assert isinstance(report, MonitoringReport)
    assert {field.name for field in fields(report)} == {
        "manifest_id",
        "runs",
        "metrics",
        "issues",
        "drift",
    }
    variants = ["STATIC_SCORE", "FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"]
    assert report.runs.variant.tolist() == variants
    assert report.runs.monitor_run_id.nunique() == 4
    assert report.runs.baseline_model_run_id.astype(str).eq(str(saved.model_run_id)).all()
    assert report.runs.baseline_deployment_id.eq(baseline.deployment_id).all()
    assert report.runs.model_name.eq(saved.model_name).all()
    assert not report.runs.deduplicated.any()
    assert set(report.metrics.variant) == set(variants)
    for _, metrics in report.metrics.groupby("variant"):
        assert {
            "row_count",
            "sample_weighted_mean_prediction",
            "sample_weighted_mean_observed",
            "deviance",
        } <= set(metrics.metric_name)
    assert (
        report.metrics.loc[report.metrics.metric_name.eq("row_count"), "metric_value"].eq(240).all()
    )
    assert set(report.issues.loc[report.issues.code.eq("CATEGORICAL_DRIFT"), "variant"]) == set(
        variants
    )
    assert report.drift.loc[report.drift.feature.eq("region"), "needs_review"].all()
    assert not report.issues.severity.eq("error").any()
    pd.testing.assert_frame_equal(dataset.df, before)
    for variant in variants:
        assert variant in caplog.text
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 4
    assert _sql_count(pricing.engine, "MODEL_RUN") == 1
    assert _sql_count(pricing.engine, "PRICING_RATE_PACKAGE") == 1
    assert _sql_count(pricing.engine, "PRICING_MODEL_DEPLOYMENT") == 1

    prepared = dataset.df
    prepared["log_exposure"] = np.log(prepared.exposure)
    with pricing.engine.connect() as connection:
        manifest = (
            connection.execute(
                text("SELECT * FROM pricing.DATASET_MANIFEST WHERE manifest_id=:id"),
                {"id": report.manifest_id},
            )
            .mappings()
            .one()
        )
        assert manifest["data_as_of_date"] == "2026-09-15"
        assert manifest["dataset_name"] == "current_claims"
        assert manifest["source_system"] == "current SQL query"
        assert manifest["data_as_of_column"] == "monitor_as_of"
        assert manifest["model_frame_sha256"] == model_frame_evidence(prepared)[0]
        assert manifest["target_column"] == "claim_count"
        assert manifest["weight_column"] is None
        assert manifest["offset_column"] == "log_exposure"
        assert manifest["offset_source_column"] == "exposure"
        assert manifest["offset_label"] == "log(exposure)"
        assert manifest["export_weight_column"] == "exposure"
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.CV_SPLIT_SET WHERE manifest_id=:id"),
                {"id": report.manifest_id},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text(
                    "SELECT COUNT(*) FROM pricing.MODEL_MONITOR_RUN WHERE run_status='SUCCESS' AND component_role='FREQUENCY'"
                )
            ).scalar_one()
            == 4
        )


def test_repeated_batch_reuses_exact_observations(fitted_case):
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    dataset = _fresh_dataset()
    options = {
        "target_column": "claim_count",
        "created_by": "test",
        "continuous_points": 9,
        "max_reml_iter": 3,
    }
    first = run_monitoring_batch(pricing.engine, baseline, dataset, **options)
    second = run_monitoring_batch(pricing.engine, baseline, dataset, **options)
    assert first.manifest_id == second.manifest_id
    assert second.runs.deduplicated.all()
    assert second.runs.monitor_run_id.tolist() == first.runs.monitor_run_id.tolist()
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 4
    assert _sql_count(pricing.engine, "DATASET_MANIFEST") == 2


@pytest.mark.parametrize("with_offset", [True, False])
def test_batch_binds_distinct_fitting_export_weights_and_saved_transforms(
    grouped_model_case, tmp_path, with_offset
):
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    dataset, spec, glm = grouped_model_case
    df = dataset.df.rename(columns={"z": "raw_z"})
    df["fit_weight"] = np.where(df.region.eq("A"), 2.0, 1.0)
    df["rating_weight"] = df.exposure * 3
    dataset = api.PricingDataset(
        df, name=dataset.name, source=dataset.source, key=dataset.key, as_of=dataset.as_of
    )
    spec = replace(
        spec,
        dataset=dataset,
        sample_weight_column="fit_weight",
        export_weight_column="rating_weight",
        transforms={
            "z": api.Clip("raw_z", lower=-1, upper=1),
            **(dict(spec.transforms) if with_offset else {}),
        },
        offset_column=spec.offset_column if with_offset else None,
        offset_source_column=spec.offset_source_column if with_offset else None,
        offset_label=spec.offset_label if with_offset else None,
    )
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    source = tmp_path / "model"
    source.mkdir()
    (source / "definition.py").write_text("# model definition\n")
    try:
        model = api.register_model(pricing, spec, source_root=source)
        candidate = api.fit_model(
            pricing,
            model=model,
            frame=api.apply_transforms(dataset.df, spec.transforms),
            superglm_model=glm,
        )
        baseline, _ = _published_baseline(pricing, model, candidate)
        raw = _fresh_dataset(weighted=True)
        current = api.PricingDataset(
            raw.df.rename(columns={"z": "raw_z"}),
            name=raw.name,
            source=raw.source,
            key=raw.key,
            as_of=raw.as_of,
        )
        report = run_monitoring_batch(
            pricing.engine,
            baseline,
            current,
            target_column="claim_count",
            created_by="test",
            continuous_points=9,
            max_reml_iter=3,
        )
        static = (
            report.metrics.loc[report.metrics.variant.eq("STATIC_SCORE")]
            .set_index("metric_name")
            .metric_value
        )
        df = current.df
        df["z"] = df.raw_z.clip(-1, 1)
        expected_mean = np.average(df.claim_count, weights=df.fit_weight)
        assert static["sample_weighted_mean_observed"] == pytest.approx(expected_mean)
        assert static["sample_weighted_mean_prediction"] == pytest.approx(
            np.average(
                baseline.predict(
                    df.loc[:, list(baseline.feature_names)],
                    offset=np.log(df.exposure) if with_offset else None,
                ),
                weights=df.fit_weight,
            )
        )
        with pricing.engine.connect() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM pricing.DATASET_MANIFEST WHERE manifest_id=:id"),
                    {"id": report.manifest_id},
                )
                .mappings()
                .one()
            )
            assert row["weight_column"] == "fit_weight"
            assert row["export_weight_column"] == "rating_weight"
            configs = (
                connection.execute(
                    text("SELECT fit_configuration_json FROM pricing.MODEL_MONITOR_RUN")
                )
                .scalars()
                .all()
            )
        for raw in configs:
            config = json.loads(raw)
            assert config["fit_sample_weight_name"] == "fit_weight"
            assert config["offset_column"] == ("log_exposure" if with_offset else None)
        assert report.drift.weight_distance.notna().all()
    finally:
        pricing.engine.dispose()


def test_batch_checks_all_variants_before_any_fit(fitted_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import batch
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    df = _fresh_dataset().df
    df["z"] = 1.0
    dataset = api.PricingDataset(df, name="current", source="test", key="id", as_of="monitor_as_of")

    def unexpected_fit(*args, **kwargs):
        pytest.fail("a refit started before all preflight checks passed")

    monkeypatch.setattr(batch, "run_monitoring_fit", unexpected_fit)
    with pytest.raises(MonitoringDataError, match="fewer than two distinct"):
        run_monitoring_batch(
            pricing.engine, baseline, dataset, target_column="claim_count", created_by="test"
        )
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 0
    assert _sql_count(pricing.engine, "MODEL_FIT_CONTRACT") == 0
    assert _sql_count(pricing.engine, "DATASET_MANIFEST") == 1


def test_batch_finishes_all_fits_before_persisting_observations(fitted_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    fit_reml = SuperGLM.fit_reml
    calls = 0

    def fail_second_refit(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated REML solver failure")
        return fit_reml(self, *args, **kwargs)

    monkeypatch.setattr(SuperGLM, "fit_reml", fail_second_refit)
    with pytest.raises(MonitoringError, match="REESTIMATE_LAMBDA.*simulated REML solver failure"):
        run_monitoring_batch(
            pricing.engine,
            baseline,
            _fresh_dataset(),
            target_column="claim_count",
            created_by="test",
            continuous_points=9,
            max_reml_iter=3,
        )
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 0
    assert _sql_count(pricing.engine, "MODEL_FIT_CONTRACT") == 0
    assert _sql_count(pricing.engine, "DATASET_MANIFEST") == 1


@pytest.mark.parametrize("missing", ["claim_count", "exposure", "z"])
def test_batch_rejects_missing_bound_columns_before_evidence(fitted_case, missing):
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    df = _fresh_dataset().df.drop(columns=missing)
    dataset = api.PricingDataset(df, name="current", source="test", key="id", as_of="monitor_as_of")
    with pytest.raises((ValueError, MonitoringError), match=missing):
        run_monitoring_batch(
            pricing.engine, baseline, dataset, target_column="claim_count", created_by="test"
        )
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 0


def test_batch_rejects_target_that_differs_from_saved_manifest(fitted_case):
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    with pytest.raises(MonitoringError, match="target_column.*baseline"):
        run_monitoring_batch(
            pricing.engine, baseline, _fresh_dataset(), target_column="exposure", created_by="test"
        )
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 0


def test_persistence_rechecks_deployment_and_retry_reuses_partial_batch(fitted_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    dataset = _fresh_dataset()
    persist = batch.persist_monitoring_fit

    def replace_deployment_after_static(engine, result, **kwargs):
        receipt = persist(engine, result, **kwargs)
        if result.variant == "STATIC_SCORE":
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts='2999-01-01'")
                )
        return receipt

    options = {
        "target_column": "claim_count",
        "created_by": "test",
        "continuous_points": 9,
        "max_reml_iter": 3,
    }
    with monkeypatch.context() as patch:
        patch.setattr(batch, "persist_monitoring_fit", replace_deployment_after_static)
        with pytest.raises(
            MonitoringError,
            match="FROZEN_REFIT persistence failed after 1 saved observations.*baseline_deployment_id",
        ):
            batch.run_monitoring_batch(pricing.engine, baseline, dataset, **options)
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 1
    with pricing.engine.begin() as connection:
        saved_id = connection.execute(
            text("SELECT monitor_run_id FROM pricing.MODEL_MONITOR_RUN")
        ).scalar_one()
        connection.execute(text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts=NULL"))
    report = batch.run_monitoring_batch(pricing.engine, baseline, dataset, **options)
    assert report.runs.deduplicated.tolist() == [True, False, False, False]
    assert report.runs.monitor_run_id.iloc[0] == saved_id
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 4
    assert _sql_count(pricing.engine, "DATASET_MANIFEST") == 2
