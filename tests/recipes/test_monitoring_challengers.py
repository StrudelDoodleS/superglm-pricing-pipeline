"""Monitoring refits publish exact, selectable packages and keep no model files."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import text
from superglm import Numeric, SuperGLM

from pricing_pipeline import notebook as api
from pricing_pipeline.modeling.monitoring import MonitoringError
from pricing_pipeline.modeling.monitoring.snapshot import restore_monitoring_snapshot
from tests.recipes.test_monitoring_batch import _fresh_dataset, _published_baseline, _sql_count


def _publication(pricing, model):
    from pricing_pipeline.modeling.monitoring.challengers import MonitoringPublicationConfig

    return MonitoringPublicationConfig(pricing.settings, model.config, model.model_id)


def _legacy_exposure_candidate(pricing, model, candidate):
    from openpyxl import load_workbook

    from pricing_pipeline.data.manifest import (
        ModelFrameManifestSpec,
        create_model_frame_manifest_with_split,
    )
    from pricing_pipeline.modeling import standard_superglm as standard
    from pricing_pipeline.modeling.standard_superglm import (
        ModelInputs,
        canonical_row_identity_index,
        export_fitted_superglm_build,
    )
    from pricing_pipeline.models.config import ValidationSplitConfig
    from pricing_pipeline.publishing.metadata import OffsetExportContract
    from pricing_pipeline.workbench.artifacts import load_candidate_bundle

    original = candidate.completed_build
    bundle = load_candidate_bundle(
        original.candidate_artifact_path,
        expected_sha256=original.candidate_artifact_sha256,
        expected_size_bytes=original.candidate_artifact_size_bytes,
        expected_format=original.candidate_artifact_format,
        expected_python_version=original.candidate_python_version,
        expected_superglm_version=original.candidate_superglm_version,
        allowed_root=pricing.settings.workbench_artifact_root,
    )
    df = api.apply_transforms(model.spec.dataset.df, model.spec.transforms)
    manifest_spec = ModelFrameManifestSpec(
        dataset_name=model.spec.dataset.name,
        source_system=model.spec.dataset.source,
        data_as_of_date=df.as_of.iloc[0],
        data_as_of_column="as_of",
        pk_columns=("id",),
        target_column="claim_count",
        feature_columns=model.spec.features,
        offset_column="log_exposure",
        offset_label="log(exposure)",
        export_weight_column="exposure",
    )
    manifest = create_model_frame_manifest_with_split(
        pricing.engine,
        frame=df,
        spec=manifest_spec,
        validation_split=ValidationSplitConfig(method="none"),
    )
    row_ids = df.loc[:, ["id"]]
    aligned = df.copy()
    aligned.index = canonical_row_identity_index(row_ids)
    inputs = ModelInputs(
        X=aligned.loc[:, list(model.spec.features)],
        y=aligned.claim_count,
        offset=aligned.log_exposure,
        export_weight=aligned.exposure,
        export_weight_name="exposure",
        row_ids=row_ids,
    )
    build = export_fitted_superglm_build(
        frame=df,
        inputs=inputs,
        fitted_model=bundle.fitted_model,
        telemetry=bundle.fitted_model.training_telemetry(),
        manifest=manifest,
        manifest_spec=manifest_spec,
        output_dir=pricing.settings.workbench_artifact_root / "legacy-offset",
        model_id=model.model_id,
        model_config=model.config,
        model_version=original.model_version,
        export_id=original.export_id,
        effective_from=None,
        model_source_sha256=original.model_source_sha256,
        created_by="test",
        offset_contract=OffsetExportContract(
            handling="ALREADY_APPLIED_SQL_EXPOSURE",
            source_name="exposure",
            label="log(exposure)",
        ),
        input_transforms=bundle.input_transforms,
    )
    # A legacy SQL exposure package applies the offset outside its rating table.
    workbook = load_workbook(build.rating_workbook_path)
    sheet = workbook["Rating Tables"]
    column = next(cell.column for cell in sheet[5] if cell.value == "Offset Multiplier")
    sheet.delete_cols(column, 3)
    workbook.save(build.rating_workbook_path)
    build = build.model_copy(
        update={"rating_workbook_sha256": standard.hash_file_sha256(build.rating_workbook_path)}
    )
    return replace(candidate, completed_build=build)


def test_legacy_sql_offset_fails_publication_preflight_but_allows_evidence_only(
    fitted_case, monkeypatch
):
    from pricing_pipeline.modeling.monitoring import batch

    pricing, model, candidate, _ = fitted_case
    legacy = _legacy_exposure_candidate(pricing, model, candidate)
    baseline, _ = _published_baseline(pricing, model, legacy)
    assert baseline.offset_contract.handling == "ALREADY_APPLIED_SQL_EXPOSURE"
    manifests = _sql_count(pricing.engine, "DATASET_MANIFEST")

    def forbidden(*args, **kwargs):
        pytest.fail("a fit started before publication compatibility was checked")

    with monkeypatch.context() as patch:
        patch.setattr(batch, "run_monitoring_fit", forbidden)
        with pytest.raises(
            MonitoringError,
            match="ALREADY_APPLIED_SQL_EXPOSURE.*automatic challenger publication",
        ):
            batch.run_monitoring_batch(
                pricing.engine,
                baseline,
                _fresh_dataset(),
                target_column="claim_count",
                created_by="test",
                publication=_publication(pricing, model),
            )
    assert _sql_count(pricing.engine, "DATASET_MANIFEST") == manifests
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 0
    assert _sql_count(pricing.engine, "MODEL_FIT_CONTRACT") == 0
    report = batch.run_monitoring_batch(
        pricing.engine,
        baseline,
        _fresh_dataset(),
        target_column="claim_count",
        created_by="test",
        continuous_points=9,
        max_reml_iter=3,
    )
    assert len(report.runs) == 4
    assert report.runs.rate_package_id.isna().all()
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 4
    assert _sql_count(pricing.engine, "PRICING_RATE_PACKAGE") == 1


@pytest.mark.parametrize("promoted_variant", ["FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"])
def test_next_sql_epoch_freezes_promoted_state_and_preserves_adaptive_policy(
    fitted_case, monkeypatch, promoted_variant
):
    from pricing_pipeline.modeling.monitoring import batch
    from tests.recipes.test_monitoring_baseline_sql import _deploy

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    options = {
        "target_column": "claim_count",
        "created_by": "test",
        "continuous_points": 9,
        "max_reml_iter": 3,
        "publication": _publication(pricing, model),
    }
    first = batch.run_monitoring_batch(pricing.engine, baseline, _fresh_dataset(), **options)
    selected = next(first.runs.loc[first.runs.variant.eq(promoted_variant)].itertuples(index=False))
    with pricing.engine.begin() as connection:
        connection.execute(
            text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts=CURRENT_TIMESTAMP")
        )
    _deploy(pricing, selected)
    assert not any(
        path.is_file() and path.suffix in {".joblib", ".xlsx", ".json"}
        for path in pricing.settings.workbench_artifact_root.rglob("*")
    )
    promoted = api.load_monitoring_baseline(pricing, model=model)
    assert str(promoted.model_run_id) == str(selected.model_run_id)
    assert promoted.identity["rate_package_id"] == selected.rate_package_id
    assert promoted.declared_monitoring_policy == baseline.declared_monitoring_policy
    if promoted_variant != "FULL_ADAPTIVE":
        assert promoted.payload()["recipe"]["features"]["x"]["knots"] is not None

    df = _fresh_dataset().df
    df["monitor_as_of"] = "2026-09-22"
    df["id"] += 100_000
    df["x"] = np.linspace(1.0, 4.0, len(df))
    dataset = api.PricingDataset(
        df, name="current_claims", source="current SQL query", key="id", as_of="monitor_as_of"
    )
    results = {}
    fit = batch.run_monitoring_fit

    def capture(*args, **kwargs):
        result = fit(*args, **kwargs)
        results[result.variant.value] = result
        return result

    monkeypatch.setattr(batch, "run_monitoring_fit", capture)
    second = batch.run_monitoring_batch(pricing.engine, promoted, dataset, **options)
    assert second.manifest_id != first.manifest_id
    assert second.runs.baseline_model_run_id.astype(str).eq(str(selected.model_run_id)).all()
    assert second.runs.baseline_deployment_id.eq(promoted.deployment_id).all()
    frozen = results["FROZEN_REFIT"]
    adaptive = results["FULL_ADAPTIVE"]
    promoted_geometry = promoted.term_metadata["x"]["fitted"]
    assert frozen.invariant_evidence.payload()["geometry"]["fitted"]["x"] == {
        name: promoted_geometry[name] for name in ("knots", "boundary")
    }
    assert {row.component_name: row.lambda_value for row in frozen.lambdas} == {
        row.component_name: row.lambda_value for row in promoted.lambdas
    }
    assert adaptive.invariant_evidence.payload()["geometry"]["fitted"]["x"]["boundary"] == [
        1.0,
        4.0,
    ]
    assert promoted_geometry["boundary"] != [1.0, 4.0]
    assert {row.lambda_mode for row in adaptive.lambdas} == {"ESTIMATED"}
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 8
    assert _sql_count(pricing.engine, "MODEL_MONITOR_PUBLICATION") == 6
    assert _sql_count(pricing.engine, "PRICING_RATE_PACKAGE") == 7
    assert _sql_count(pricing.engine, "PRICING_MODEL_DEPLOYMENT") == 2
    assert api.load_monitoring_baseline(pricing, model=model).model_run_id == promoted.model_run_id


def test_batch_publishes_the_exact_three_refits_without_refitting_or_kept_files(
    fitted_case, monkeypatch
):
    from pricing_pipeline.modeling.monitoring import batch

    pricing, model, candidate, _ = fitted_case
    baseline, champion = _published_baseline(pricing, model, candidate)
    dataset = _fresh_dataset()
    publication = _publication(pricing, model)
    before_files = {
        path for path in pricing.settings.workbench_artifact_root.rglob("*") if path.is_file()
    }
    expected = {}
    run_fit = batch.run_monitoring_fit

    def forbidden(*args, **kwargs):
        pytest.fail("challenger export fitted or cloned a model")

    def capture_exact_fit(*args, **kwargs):
        result = run_fit(*args, **kwargs)
        expected[result.variant.value] = result.fitted_model.predict(
            args[1], offset=kwargs["offset"]
        ).copy()
        if result.variant == "FULL_ADAPTIVE":
            for name in ("fit", "fit_reml", "clone_unfitted"):
                monkeypatch.setattr(SuperGLM, name, forbidden)
        return result

    monkeypatch.setattr(batch, "run_monitoring_fit", capture_exact_fit)
    report = batch.run_monitoring_batch(
        pricing.engine,
        baseline,
        dataset,
        target_column="claim_count",
        created_by="weekly-test",
        continuous_points=9,
        max_reml_iter=3,
        publication=publication,
    )
    assert report.runs.role.tolist() == ["CHAMPION", "CHALLENGER", "CHALLENGER", "CHALLENGER"]
    assert report.runs.iloc[0][["model_run_id", "rate_package_id", "package_version"]].isna().all()
    challengers = report.runs.iloc[1:]
    assert challengers.rate_package_id.nunique() == 3
    assert challengers.baseline_rate_package_id.eq(champion.rate_package_id).all()
    assert challengers.baseline_model_run_id.astype(str).eq(str(champion.model_run_id)).all()
    assert challengers.baseline_deployment_id.eq(baseline.deployment_id).all()
    assert set(challengers.package_version) == {2, 3, 4}
    assert _sql_count(pricing.engine, "PRICING_RATE_PACKAGE") == 4
    assert _sql_count(pricing.engine, "MODEL_RUN") == 4
    assert _sql_count(pricing.engine, "PRICING_MODEL_DEPLOYMENT") == 1
    assert _sql_count(pricing.engine, "MODEL_MONITOR_RUN") == 4
    with pricing.engine.connect() as connection:
        for row in challengers.itertuples():
            saved = (
                connection.execute(
                    text(
                        "SELECT snapshot_json,snapshot_sha256 FROM pricing.MODEL_MONITORING_BASELINE WHERE model_run_id=:run"
                    ),
                    {"run": row.model_run_id},
                )
                .mappings()
                .one()
            )
            restored = restore_monitoring_snapshot(
                saved["snapshot_json"], expected_sha256=saved["snapshot_sha256"]
            )
            df = dataset.df
            np.testing.assert_allclose(
                restored.predict(
                    df.loc[:, list(baseline.feature_names)], offset=np.log(df.exposure)
                ),
                expected[row.variant],
                rtol=1e-12,
                atol=1e-13,
            )
            metadata = (
                connection.execute(
                    text(
                        "SELECT mr.split_set_id, recipe.recipe_json FROM pricing.MODEL_RUN mr JOIN pricing.MODEL_RECIPE recipe ON recipe.recipe_id=mr.recipe_id WHERE mr.model_run_id=:run"
                    ),
                    {"run": row.model_run_id},
                )
                .mappings()
                .one()
            )
            assert metadata["split_set_id"] is None
            assert json.loads(metadata["recipe_json"])["validation"] == {"type": "none"}
    assert {
        path for path in pricing.settings.workbench_artifact_root.rglob("*") if path.is_file()
    } == before_files


@pytest.mark.parametrize("baseline_kind", ["RAW", "EDITOR_EDIT"])
def test_identical_rates_remain_three_distinct_challenger_publications(
    grouped_model_case, tmp_path, baseline_kind
):
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    dataset, spec, _ = grouped_model_case
    spec = replace(spec, features=("z",))
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    source = tmp_path / "model"
    source.mkdir()
    (source / "definition.py").write_text("# numeric monitoring model\n")
    try:
        model = api.register_model(pricing, spec, source_root=source)
        candidate = api.fit_model(
            pricing,
            model=model,
            frame=api.apply_transforms(dataset.df, spec.transforms),
            superglm_model=SuperGLM(
                features={"z": Numeric()}, selection_penalty=0, retain_fit_state=False
            ),
            model_kind=baseline_kind,
        )
        baseline, _ = _published_baseline(pricing, model, candidate)
        report = run_monitoring_batch(
            pricing.engine,
            baseline,
            _fresh_dataset(),
            target_column="claim_count",
            created_by="test",
            continuous_points=9,
            max_reml_iter=3,
            publication=_publication(pricing, model),
        )
        assert report.runs.iloc[1:].rate_package_id.nunique() == 3
        with pricing.engine.connect() as connection:
            digests = (
                connection.execute(
                    text(
                        "SELECT model_equivalence_sha256 FROM pricing.MODEL_RUN WHERE model_run_id != :baseline"
                    ),
                    {"baseline": baseline.model_run_id},
                )
                .scalars()
                .all()
            )
            kinds = (
                connection.execute(
                    text(
                        "SELECT model_kind FROM pricing.MODEL_RUN WHERE model_run_id != :baseline"
                    ),
                    {"baseline": baseline.model_run_id},
                )
                .scalars()
                .all()
            )
        assert len(digests) == 3
        assert len(set(digests)) == 1
        assert kinds == ["RAW", "RAW", "RAW"]
    finally:
        pricing.engine.dispose()


def test_retry_reuses_linked_packages_without_another_export(fitted_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import batch, challengers

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    dataset = _fresh_dataset()
    options = {
        "target_column": "claim_count",
        "created_by": "test",
        "continuous_points": 9,
        "max_reml_iter": 3,
        "publication": _publication(pricing, model),
    }
    first = batch.run_monitoring_batch(pricing.engine, baseline, dataset, **options)

    def forbidden(*args, **kwargs):
        pytest.fail("an exact monitoring retry exported another package")

    monkeypatch.setattr(challengers, "export_fitted_superglm_build", forbidden)
    second = batch.run_monitoring_batch(pricing.engine, baseline, dataset, **options)
    assert (
        first.runs.iloc[1:].rate_package_id.tolist()
        == second.runs.iloc[1:].rate_package_id.tolist()
    )
    assert second.runs.iloc[1:].publication_reused.all()
    assert _sql_count(pricing.engine, "PRICING_RATE_PACKAGE") == 4


@pytest.mark.parametrize("failure_stage", ["export", "publication"])
def test_export_failure_cleans_all_transient_model_files(fitted_case, monkeypatch, failure_stage):
    from pricing_pipeline.modeling import standard_superglm
    from pricing_pipeline.modeling.monitoring import challengers
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    publication = _publication(pricing, model)
    root = pricing.settings.workbench_artifact_root
    before = set(root.rglob("*"))

    def fail_after_workbook(*args, output_path, **kwargs):
        output_path.write_bytes(b"partial workbook")
        raise RuntimeError("simulated challenger failure")

    def fail_publication(engine, request):
        assert Path(request.build.candidate_artifact_path).is_file()
        assert Path(request.build.rating_workbook_path).is_file()
        assert Path(request.build.publication_receipt_path).is_file()
        raise RuntimeError("simulated challenger failure")

    if failure_stage == "export":
        monkeypatch.setattr(standard_superglm, "export_rating_tables", fail_after_workbook)
    else:
        monkeypatch.setattr(challengers, "publish_candidate", fail_publication)
    with pytest.raises(MonitoringError, match="FROZEN_REFIT.*simulated challenger failure"):
        run_monitoring_batch(
            pricing.engine,
            baseline,
            _fresh_dataset(),
            target_column="claim_count",
            created_by="test",
            continuous_points=9,
            max_reml_iter=3,
            publication=publication,
        )
    assert set(root.rglob("*")) == before
    assert _sql_count(pricing.engine, "PRICING_RATE_PACKAGE") == 1


def test_challenger_rejects_estimator_changed_after_observation(fitted_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import batch

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    publication = _publication(pricing, model)
    persist = batch.persist_monitoring_fit

    def corrupt_after_persistence(engine, result, **kwargs):
        receipt = persist(engine, result, **kwargs)
        if result.variant == "FROZEN_REFIT":
            fitted = result.fitted_model
            fitted._result = replace(fitted._result, beta=fitted.result.beta + 0.5)
        return receipt

    monkeypatch.setattr(batch, "persist_monitoring_fit", corrupt_after_persistence)
    with pytest.raises(MonitoringError, match="fitted.*evidence|evidence.*fitted"):
        batch.run_monitoring_batch(
            pricing.engine,
            baseline,
            _fresh_dataset(),
            target_column="claim_count",
            created_by="test",
            continuous_points=9,
            max_reml_iter=3,
            publication=publication,
        )
    assert _sql_count(pricing.engine, "PRICING_RATE_PACKAGE") == 1
