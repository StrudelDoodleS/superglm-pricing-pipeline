"""A fitted export must preserve the estimator and omit unperformed validation."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from superglm import SuperGLM

from pricing_pipeline import notebook as api
from pricing_pipeline.data.manifest import (
    DatasetManifestResult,
    ModelFrameManifestSpec,
    model_frame_evidence,
)
from pricing_pipeline.modeling.standard_superglm import ModelInputs, canonical_row_identity_index
from pricing_pipeline.models.config import ValidationSplitConfig
from pricing_pipeline.workbench.artifacts import load_candidate_bundle


def test_export_existing_fitted_model_performs_no_fit_clone_cv_or_manifest_write(
    fitted_case, tmp_path, monkeypatch
):
    from pricing_pipeline.modeling import standard_superglm as standard

    export = getattr(standard, "export_fitted_superglm_build", None)
    assert callable(export), "the standard builder needs a reusable fitted-model export"
    _, model, candidate, _ = fitted_case
    source = candidate.completed_build
    bundle = load_candidate_bundle(
        source.candidate_artifact_path,
        expected_sha256=source.candidate_artifact_sha256,
        expected_size_bytes=source.candidate_artifact_size_bytes,
        expected_format=source.candidate_artifact_format,
        expected_python_version=source.candidate_python_version,
        expected_superglm_version=source.candidate_superglm_version,
        allowed_root=tmp_path,
    )
    fitted = bundle.fitted_model
    df = api.apply_transforms(model.spec.dataset.df, model.spec.transforms)
    rows = df.loc[:, ["id"]]
    aligned = df.copy()
    aligned.index = canonical_row_identity_index(rows)
    inputs = ModelInputs(
        X=aligned.loc[:, list(model.spec.features)],
        y=aligned.claim_count,
        offset=aligned.log_exposure,
        offset_source=aligned.exposure,
        offset_source_name="exposure",
        export_weight=aligned.exposure,
        export_weight_name="exposure",
        row_ids=rows,
    )
    expected = fitted.predict(inputs.X, offset=inputs.offset).copy()
    telemetry = fitted.training_telemetry()

    def forbidden(*args, **kwargs):
        pytest.fail("fitted-model export performed a fit, clone, CV or manifest write")

    for name in ("fit", "fit_reml", "clone_unfitted"):
        monkeypatch.setattr(SuperGLM, name, forbidden)
    for name in (
        "run_cross_validation",
        "fit_full_model",
        "create_model_frame_manifest_with_split",
    ):
        monkeypatch.setattr(standard, name, forbidden)
    manifest = DatasetManifestResult("monitoring-current", model_frame_evidence(df)[0])
    build = export(
        frame=df,
        inputs=inputs,
        fitted_model=fitted,
        telemetry=telemetry,
        manifest=manifest,
        manifest_spec=ModelFrameManifestSpec(
            dataset_name="current",
            source_system="test",
            data_as_of_date="2026-09-15",
            pk_columns=("id",),
            target_column="claim_count",
            feature_columns=tuple(model.spec.features),
            offset_column="log_exposure",
            offset_source_column="exposure",
            offset_label="log(exposure)",
            export_weight_column="exposure",
        ),
        output_dir=tmp_path / "export",
        model_id=model.model_id,
        model_config=model.config,
        model_version="v2",
        export_id="monitoring-exact-export",
        effective_from=None,
        model_source_sha256=source.model_source_sha256,
        created_by="test",
        offset_contract=bundle.offset_contract,
        input_transforms=bundle.input_transforms,
        recipe_capture=source.recipe_capture,
    )
    restored = load_candidate_bundle(
        build.candidate_artifact_path,
        expected_sha256=build.candidate_artifact_sha256,
        expected_size_bytes=build.candidate_artifact_size_bytes,
        expected_format=build.candidate_artifact_format,
        expected_python_version=build.candidate_python_version,
        expected_superglm_version=build.candidate_superglm_version,
        allowed_root=tmp_path,
    )
    np.testing.assert_array_equal(
        restored.fitted_model.predict(inputs.X, offset=inputs.offset), expected
    )
    pd.testing.assert_frame_equal(restored.X, inputs.X)
    assert restored.cv_report["scope"] == "full_fit"
    assert restored.cv_report["validation_performed"] is False
    assert restored.cv_report["full_fit_telemetry"] == telemetry
    assert build.split_set_id is None
    assert build.fold_metrics == ()
    assert set(build.metric_scopes.values()) == {"full_fit"}
    assert not any(name.startswith("cv_") for name in build.metrics)
    assert Path(build.rating_workbook_path).exists()
    assert build.model_source_sha256 == source.model_source_sha256


def test_monitoring_recipe_round_trip_explicitly_records_no_validation(grouped_model_case):
    from pricing_pipeline.modeling.recipes import ModelRecipe

    dataset, spec, glm = grouped_model_case
    spec = replace(spec, validation=ValidationSplitConfig(method="none"))
    recipe = ModelRecipe.from_model(glm, spec=spec)
    assert recipe.document.to_dict()["validation"] == {"type": "none"}
    rebuilt_spec, rebuilt_model = recipe.build(dataset=dataset)
    assert rebuilt_spec.validation.method == "none"
    assert ModelRecipe.from_model(rebuilt_model, spec=rebuilt_spec).sha256 == recipe.sha256


def test_explicit_no_validation_training_has_no_cv_calls_splits_or_metrics(
    grouped_model_case, tmp_path, monkeypatch
):
    from pricing_pipeline.modeling import standard_superglm as standard

    dataset, spec, glm = grouped_model_case
    spec = replace(spec, validation=ValidationSplitConfig(method="none"))

    def forbidden(*args, **kwargs):
        pytest.fail("an explicit no-validation fit ran cross-validation")

    monkeypatch.setattr(standard, "run_cross_validation", forbidden)
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    source = tmp_path / "model"
    source.mkdir()
    (source / "definition.py").write_text("# no-validation fit\n")
    try:
        model = api.register_model(pricing, spec, source_root=source)
        candidate = api.fit_model(
            pricing,
            model=model,
            frame=api.apply_transforms(dataset.df, spec.transforms),
            superglm_model=glm,
        )
        build = candidate.completed_build
        assert build.split_set_id is None
        assert build.fold_metrics == ()
        assert set(build.metric_scopes.values()) == {"full_fit"}
        assert candidate.recipe.document.to_dict()["validation"] == {"type": "none"}
    finally:
        pricing.engine.dispose()


def test_monitoring_schedule_sources_do_not_change_the_training_definition_hash(tmp_path):
    from pricing_pipeline.modeling.standard_superglm import hash_model_source

    definition = tmp_path / "definition.py"
    definition.write_text("model_feature = 'x'\n")
    original = hash_model_source(tmp_path)
    script = tmp_path / "monitoring.py"
    notebook = tmp_path / "07_optional_test_weekly_run.ipynb"
    script.write_text("weekly_query = 'original'\n")
    notebook.write_text('{"cells": [{"cell_type": "code", "source": ["run()"]}]}')
    assert hash_model_source(tmp_path) == original
    script.write_text("weekly_query = 'changed'\n")
    notebook.write_text('{"cells": [{"cell_type": "code", "source": ["display(report)"]}]}')
    assert hash_model_source(tmp_path) == original
    imported = tmp_path / "features" / "monitoring.py"
    imported.parent.mkdir()
    imported.write_text("model_transform = 1\n")
    with_module = hash_model_source(tmp_path)
    assert with_module != original
    imported.write_text("model_transform = 2\n")
    assert hash_model_source(tmp_path) != with_module
