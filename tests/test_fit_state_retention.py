"""Retaining training caches must not change grouping, configuration or predictions."""

import io

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import KFold
from superglm import Categorical, Spline, SuperGLM, collapse_levels, cross_validate

from pricing_pipeline.modeling.monitoring import MonitoringVariant, run_monitoring_fit
from pricing_pipeline.modeling.standard_superglm import (
    ModelInputs,
    fit_full_model,
    run_cross_validation,
)
from pricing_pipeline.notebook import apply_level_groupings


@pytest.mark.parametrize("fit_mode", ["fit", "fit_reml"])
def test_grouped_cv_and_full_fit_preserve_configuration_and_retention(fit_mode):
    rng = np.random.default_rng(9813)
    df = pd.DataFrame(
        {
            "region": np.resize(["A", "B", "C"], 180),
            "x": rng.uniform(0, 3, 180),
        }
    )
    offset = np.log(rng.uniform(0.3, 1.5, len(df)))
    weights = rng.integers(1, 4, len(df)).astype(float)
    y = rng.poisson(np.exp(0.4 + 0.2 * df.x + 0.3 * df.region.ne("A") + offset))
    grouping = collapse_levels(df.region, groups={"BC": ["B", "C"]})
    original = {"region": Categorical(base="A"), "x": Spline("cr", k=3, knot_strategy="quantile")}
    inputs = ModelInputs(X=df, y=y, sample_weight=weights, offset=offset)
    splits = list(KFold(n_splits=3, shuffle=True, random_state=42).split(df))
    oof_predictions, full_predictions = [], []

    for retain in (True, False):
        model = SuperGLM(
            family="poisson",
            features=apply_level_groupings(original, {"region": grouping}),
            selection_penalty=0.0,
            discrete=True,
            n_bins=32,
            tol=1e-7,
            max_iter=150,
            weight_semantics="frequency",
            retain_fit_state=retain,
        )
        captured = []

        def capture_estimators(*args, captured=captured, **kwargs):
            assert kwargs["return_estimators"] is False
            kwargs["return_estimators"] = True  # Inspect the real CV clones in this test only.
            result = cross_validate(*args, **kwargs)
            captured.extend(result.estimators)
            oof_predictions.append(result.oof_predictions)
            return result

        evidence = run_cross_validation(
            model.clone_unfitted(),
            inputs,
            split_indices=splits,
            fit_mode=fit_mode,
            scoring="deviance",
            cross_validate_fn=capture_estimators,
        )
        assert len(captured) == 3
        assert len(evidence.fold_metrics) == 3
        fitted, _ = fit_full_model(model.clone_unfitted(), inputs, fit_mode=fit_mode)
        assert fitted.result.converged
        artifact = io.BytesIO()
        joblib.dump(fitted, artifact, compress=3)
        artifact.seek(0)
        restored = joblib.load(artifact)

        for checked in (model, *captured, fitted, restored):
            config = checked._config
            assert config.retain_fit_state is retain
            assert checked._retain_fit_state is retain
            assert config.discrete is True and config.n_bins == 32
            assert config.tol == 1e-7 and config.max_iter == 150
            assert config.weight_semantics == "frequency"
            assert config.family == "poisson"
            assert checked._specs["region"]._grouping == grouping
            assert checked._specs["region"].base == "A"
            assert checked._specs["x"].knot_strategy == "quantile"
            assert checked._specs["x"].n_knots == 1
        for checked in (*captured, fitted, restored):
            assert (checked._dm is None) is (not retain)
            assert (checked._fit_X_ref is None) is (not retain)
            assert checked.summary() is not None
            probe = pd.DataFrame({"region": ["B", "C"], "x": [1.5, 1.5]})
            prediction = checked.predict(probe, offset=np.zeros(2))
            assert prediction[0] == pytest.approx(prediction[1], rel=1e-12)
        full_predictions.append(restored.predict(df, offset=offset))

    assert original["region"]._grouping is None
    np.testing.assert_allclose(oof_predictions[0], oof_predictions[1], rtol=1e-10, atol=1e-12)
    np.testing.assert_allclose(full_predictions[0], full_predictions[1], rtol=1e-10, atol=1e-12)


def test_monitoring_freeze_rules_survive_released_fit_state():
    rng = np.random.default_rng(1816)
    df = pd.DataFrame({"region": np.resize(["A", "B", "C"], 240), "x": np.linspace(0, 1, 240)})
    grouping = collapse_levels(df.region, groups={"BC": ["B", "C"]})
    baseline = SuperGLM(
        family="poisson",
        selection_penalty=0,
        retain_fit_state=False,
        features={
            "region": Categorical(base="A", grouping=grouping),
            "x": Spline("cr", k=5, knot_strategy="quantile"),
        },
    ).fit_reml(df, rng.poisson(np.exp(0.8 + 0.7 * df.x + df.x**2)))
    # New data has different quantiles and omits one original grouped level.
    new_df = pd.DataFrame(
        {"region": np.resize(["A", "B"], 240), "x": np.linspace(0.2, 0.9, 240) ** 2}
    )
    new_y = rng.poisson(np.exp(0.6 + 1.2 * new_df.x**2))
    baseline_knots = baseline._specs["x"].fitted_knots.copy()
    baseline_lambdas = baseline.reml_diagnostics()["lambdas"]
    results = {
        variant: run_monitoring_fit(
            baseline,
            new_df,
            new_y,
            variant=variant,
            continuous_points=11,
            max_reml_iter=20,
        )
        for variant in MonitoringVariant
    }
    points = {
        (r.term_name, r.point_key) for r in results[MonitoringVariant.STATIC_SCORE].relativities
    }
    assert results[MonitoringVariant.STATIC_SCORE].fitted_model is baseline
    for result in results.values():
        fitted = result.fitted_model
        assert result.invariant_evidence.status == "VERIFIED"
        assert fitted._config.retain_fit_state is False
        assert fitted._dm is None and fitted._fit_X_ref is None
        assert fitted._specs["region"]._grouping == grouping
        assert fitted._specs["region"]._base_level == baseline._specs["region"]._base_level
        assert set(fitted._specs) == set(baseline._specs)
        assert fitted._specs["x"].n_knots == baseline._specs["x"].n_knots
        assert {(r.term_name, r.point_key) for r in result.relativities} == points
    for variant in (MonitoringVariant.FROZEN_REFIT, MonitoringVariant.REESTIMATE_LAMBDA):
        fitted = results[variant].fitted_model
        np.testing.assert_array_equal(fitted._specs["x"].fitted_knots, baseline_knots)
        assert fitted._specs["x"]._lo == baseline._specs["x"]._lo
        assert fitted._specs["x"]._hi == baseline._specs["x"]._hi
    frozen = results[MonitoringVariant.FROZEN_REFIT]
    assert {row.component_name: row.lambda_value for row in frozen.lambdas} == baseline_lambdas
    assert frozen.fitted_model.reml_diagnostics()["termination_reason"] == "fixed_lambdas"
    for variant in (MonitoringVariant.REESTIMATE_LAMBDA, MonitoringVariant.FULL_ADAPTIVE):
        assert {row.lambda_mode for row in results[variant].lambdas} == {"ESTIMATED"}
    assert not np.array_equal(
        results[MonitoringVariant.FULL_ADAPTIVE].fitted_model._specs["x"].fitted_knots,
        baseline_knots,
    )
