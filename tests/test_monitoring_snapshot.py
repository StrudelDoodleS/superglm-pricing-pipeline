"""SQL snapshots preserve predictions and refit intent without fitted objects."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from superglm import Categorical, Numeric, OrderedCategorical, Spline, SuperGLM, collapse_levels

from pricing_pipeline.modeling.monitoring import (
    build_model_fit_contract,
    materialize_monitoring_model,
)
from pricing_pipeline.modeling.monitoring.evidence import _result_relativities
from pricing_pipeline.publishing.metadata import OffsetExportContract


def _case(kind="cr", retain=False):
    rng = np.random.default_rng(91)
    n = 240
    X = pd.DataFrame(
        {
            "x": np.linspace(0.0, 1.0, n),
            "numeric": rng.normal(size=n),
            "category": np.tile(["A", "B", "C", "D"], n // 4),
            "ordered": np.tile([1, 2, 3, 4, 5, "Unknown"], n // 6),
        }
    )
    X["ordered"] = pd.Series(np.tile(np.array([1, 2, 3, 4, 5, "Unknown"], dtype=object), n // 6))
    weights = rng.integers(1, 4, n).astype(float)
    offset = rng.normal(0, 0.1, n)
    y = rng.poisson(np.exp(0.1 + np.sin(X.x * 4) + 0.1 * X.numeric + offset))
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        retain_fit_state=retain,
        discrete=True,
        n_bins=64,
        weight_semantics="frequency",
        features={
            "x": Spline(kind, k=5),
            "numeric": Numeric(),
            "category": Categorical(
                grouping=collapse_levels(X.category, groups={"AB": ["A", "B"]}), base="AB"
            ),
            "ordered": OrderedCategorical(
                order=[1, 2, 3, 4, 5], specials=["Unknown"], basis=Spline("ps", k=5), base=1
            ),
        },
    ).fit_reml(X, y, weights, offset, max_reml_iter=5, runtime_validation="skip")
    bundle = SimpleNamespace(
        fitted_model=model,
        X=X,
        y=y,
        sample_weight=weights,
        offset_contract=OffsetExportContract(
            handling="ALREADY_APPLIED_SQL_EXPOSURE",
            source_name="exposure",
            label="runtime exposure",
        ),
        fit_sample_weight_name="weight",
        export_weight_name=None,
        input_transforms=None,
        model_name="test",
        model_version="1",
        export_id="export",
        manifest_id="manifest",
        split_set_id=None,
        row_order_sha256="a" * 64,
        model_source_sha256="b" * 64,
        model_frame_sha256="c" * 64,
    )
    return bundle, offset


def _round_trip(bundle):
    from pricing_pipeline.modeling.monitoring.snapshot import (
        capture_monitoring_snapshot,
        restore_monitoring_snapshot,
    )

    snapshot = capture_monitoring_snapshot(bundle)
    return snapshot, restore_monitoring_snapshot(
        snapshot.snapshot_json, expected_sha256=snapshot.snapshot_sha256
    )


@pytest.mark.parametrize("kind", ["ps", "cr", "bs", "ns"])
@pytest.mark.parametrize("retain", [False, True])
def test_snapshot_preserves_static_predictions_metrics_and_relativities(kind, retain):
    bundle, offset = _case(kind, retain)
    snapshot, baseline = _round_trip(bundle)
    fresh = bundle.X.copy()
    fresh["x"] = np.linspace(-0.15, 1.15, len(fresh))
    expected = bundle.fitted_model.predict(fresh, offset=offset)
    np.testing.assert_allclose(
        baseline.predict(fresh, offset=offset), expected, rtol=1e-10, atol=1e-11
    )
    actual_metrics = baseline.metrics(fresh, bundle.y, bundle.sample_weight, offset)
    native_metrics = bundle.fitted_model.metrics(fresh, bundle.y, bundle.sample_weight, offset)
    for name in ("deviance", "null_deviance", "explained_deviance", "log_likelihood"):
        assert getattr(actual_metrics, name) == pytest.approx(
            getattr(native_metrics, name), rel=1e-10, abs=1e-10
        )
    contract = build_model_fit_contract(
        bundle.fitted_model,
        offset_contract=bundle.offset_contract,
        fit_sample_weight_name="weight",
        continuous_points=13,
    )
    assert baseline.model_fit_contract(13).payload() == contract.payload()
    native_rows = _result_relativities(bundle.fitted_model, contract.payload()["evaluation_grid"])
    actual_rows = baseline.relativities(contract.payload()["evaluation_grid"])
    assert len(actual_rows) == len(native_rows)
    for actual, native in zip(actual_rows, native_rows, strict=True):
        assert actual.point_key == native.point_key
        assert actual.log_relativity == pytest.approx(native.log_relativity, abs=1e-10)
    payload = json.loads(snapshot.snapshot_json)
    assert payload["reference_profiles"]["category"]
    assert not any(key in payload for key in ("X", "y", "sample_weight", "offset", "fitted_model"))


@pytest.mark.parametrize("variant", ["FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"])
def test_snapshot_refit_matches_native_controlled_refit(variant):
    bundle, offset = _case()
    _, baseline = _round_trip(bundle)
    fresh = bundle.X.copy()
    fresh["x"] = fresh.x * 0.8 + 0.1
    native = materialize_monitoring_model(bundle.fitted_model, variant)
    restored = baseline.materialize(variant)
    for model in (native, restored):
        model.fit_reml(
            fresh,
            bundle.y,
            bundle.sample_weight,
            offset,
            max_reml_iter=5,
            runtime_validation="skip",
        )
    np.testing.assert_allclose(
        restored.predict(fresh, offset), native.predict(fresh, offset), rtol=1e-9, atol=1e-10
    )


def test_snapshot_rejects_bad_digest_and_unknown_schema():
    from pricing_pipeline.modeling.monitoring import MonitoringError
    from pricing_pipeline.modeling.monitoring.contracts import _canonical_json, _sha256_text
    from pricing_pipeline.modeling.monitoring.snapshot import restore_monitoring_snapshot

    bundle, _ = _case()
    snapshot, _ = _round_trip(bundle)
    with pytest.raises(MonitoringError, match="digest"):
        restore_monitoring_snapshot(snapshot.snapshot_json, expected_sha256="0" * 64)
    payload = json.loads(snapshot.snapshot_json)
    payload["schema_version"] = 999
    text = _canonical_json(payload)
    with pytest.raises(MonitoringError, match="schema"):
        restore_monitoring_snapshot(text, expected_sha256=_sha256_text(text))


def _simple_bundle(model, X, y, weights=None):
    return SimpleNamespace(
        fitted_model=model,
        X=X,
        y=y,
        sample_weight=weights,
        offset_contract=OffsetExportContract(handling="NONE"),
        fit_sample_weight_name="weight" if weights is not None else None,
        export_weight_name=None,
        input_transforms=None,
        model_name="test",
        model_version="1",
        export_id="export",
        manifest_id="manifest",
        split_set_id=None,
        row_order_sha256="a" * 64,
        model_source_sha256="b" * 64,
        model_frame_sha256="c" * 64,
    )


@pytest.mark.parametrize("kind", ["ps", "cr", "bs", "ns"])
def test_snapshot_preserves_extended_spline_tails(kind):
    X = pd.DataFrame({"x": np.linspace(0.0, 1.0, 100)})
    y = np.exp(np.sin(X.x * 3))
    model = SuperGLM(
        family="gamma",
        selection_penalty=0.0,
        features={"x": Spline(kind, k=5, extrapolation="extend")},
    ).fit(X, y)
    _, baseline = _round_trip(_simple_bundle(model, X, y))
    fresh = pd.DataFrame({"x": [-2.0, -0.3, 0.0, 0.5, 1.0, 1.8, 3.0]})
    np.testing.assert_allclose(
        baseline.predict(fresh), model.predict(fresh), rtol=1e-10, atol=1e-11
    )


@pytest.mark.parametrize("family", ["gaussian", "gamma", "tweedie"])
@pytest.mark.parametrize("semantics", ["prior", "frequency"])
def test_snapshot_metrics_preserve_fitted_dispersion_and_family(family, semantics):
    from superglm.distributions import Tweedie

    rng = np.random.default_rng(971)
    X = pd.DataFrame({"x": np.linspace(-1, 1, 150)})
    y = rng.gamma(2, 0.8, len(X))
    weights = rng.integers(1, 4, len(X)).astype(float)
    distribution = Tweedie(p=1.6) if family == "tweedie" else family
    model = SuperGLM(
        family=distribution,
        selection_penalty=0.0,
        weight_semantics=semantics,
        features={"x": Numeric()},
    ).fit(X, y, weights)
    _, baseline = _round_trip(_simple_bundle(model, X, y, weights))
    assert baseline.payload()["prediction"]["phi"] == model.result.phi
    actual, native = baseline.metrics(X.copy(), y, weights), model.metrics(X.copy(), y, weights)
    for name in ("deviance", "null_deviance", "explained_deviance", "log_likelihood"):
        assert getattr(actual, name) == pytest.approx(getattr(native, name), abs=1e-10)


def test_snapshot_preserves_typed_levels_and_unseen_base():
    X = pd.DataFrame({"x": np.tile(np.array([1, "1", "base"], dtype=object), 40)})
    y = np.tile([1, 3, 2], 40)
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": Categorical(base="base", unseen="base")},
    ).fit(X, y)
    _, baseline = _round_trip(_simple_bundle(model, X, y))
    fresh = pd.DataFrame({"x": np.array([1.0, "1", "base", "new"], dtype=object)})
    with pytest.warns(UserWarning, match="unseen"):
        actual = baseline.predict(fresh)
    with pytest.warns(UserWarning, match="unseen"):
        expected = model.predict(fresh)
    np.testing.assert_allclose(actual, expected, rtol=1e-12)
    assert actual[0] != actual[1]


@pytest.mark.parametrize("variant", ["FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"])
def test_snapshot_refit_preserves_inferred_type_distinct_categorical_levels(variant):
    X = pd.DataFrame({"x": np.tile(np.array([1, "1", "base"], dtype=object), 40)})
    y = np.tile([1, 3, 2], 40)
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": Categorical(base="base", unseen="base")},
    ).fit(X, y)
    _, baseline = _round_trip(_simple_bundle(model, X, y))
    fresh_y = np.tile([2, 5, 3], 40)
    native = materialize_monitoring_model(model, variant)
    native.fit_reml(X, fresh_y, max_reml_iter=5, runtime_validation="skip")
    restored = baseline.materialize(variant)
    restored.fit_reml(X, fresh_y, max_reml_iter=5, runtime_validation="skip")

    np.testing.assert_allclose(restored.predict(X), native.predict(X), rtol=1e-12, atol=1e-12)
    assert restored.predict(X)[0] != restored.predict(X)[1]
    np.testing.assert_array_equal(restored._specs["x"]._levels, native._specs["x"]._levels)


def test_snapshot_identity_properties_require_binding():
    from dataclasses import replace

    from pricing_pipeline.modeling.monitoring import MonitoringError

    bundle, _ = _case()
    _, baseline = _round_trip(bundle)
    with pytest.raises(MonitoringError, match="identity"):
        _ = baseline.model_run_id
    bound = replace(baseline, identity={"model_run_id": 23, "deployment_id": 4})
    assert bound.model_run_id == 23
    assert bound.deployment_id == 4
    assert bound.feature_names == tuple(bundle.fitted_model._feature_order)


@pytest.mark.parametrize(
    "field", ["terms", "lambdas", "normalized_structure", "telemetry", "reference_profiles"]
)
def test_snapshot_rejects_internally_inconsistent_evidence(field):
    from pricing_pipeline.modeling.monitoring import MonitoringError
    from pricing_pipeline.modeling.monitoring.contracts import _canonical_json, _sha256_text
    from pricing_pipeline.modeling.monitoring.snapshot import restore_monitoring_snapshot

    bundle, _ = _case()
    snapshot, _ = _round_trip(bundle)
    payload = json.loads(snapshot.snapshot_json)
    if field == "terms":
        payload[field][0]["metadata_json"] = "{}"
    elif field == "lambdas":
        payload[field][0]["lambda_value"] += 1
    elif field == "normalized_structure" or field == "telemetry":
        payload[field]["model"] = {}
    else:
        first = next(iter(payload[field]["category"].values()))
        first["rows"] += 100
    encoded = _canonical_json(payload)
    with pytest.raises(MonitoringError):
        restore_monitoring_snapshot(encoded, expected_sha256=_sha256_text(encoded))


def test_snapshot_non_reml_baseline_materializes_like_native():
    X = pd.DataFrame({"x": np.linspace(0, 1, 100)})
    y = np.exp(np.sin(X.x * 3))
    model = SuperGLM(
        family="gamma", selection_penalty=0.0, spline_penalty=3.5, features={"x": Spline("cr", k=5)}
    ).fit(X, y)
    _, baseline = _round_trip(_simple_bundle(model, X, y))
    actual, native = (
        baseline.materialize("FROZEN_REFIT"),
        materialize_monitoring_model(model, "FROZEN_REFIT"),
    )
    for fitted in (actual, native):
        fitted.fit_reml(X, y, max_reml_iter=5, runtime_validation="skip")
    np.testing.assert_allclose(actual.predict(X), native.predict(X), rtol=1e-10, atol=1e-11)


def test_snapshot_marks_ordered_polynomial_basis_as_unsupported():
    from superglm import Polynomial

    from pricing_pipeline.modeling.monitoring.snapshot import (
        MonitoringSnapshotUnsupported,
        capture_monitoring_snapshot,
    )

    X = pd.DataFrame({"x": np.tile([1, 2, 3], 30)})
    y = np.tile([1, 2, 4], 30)
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": OrderedCategorical(order=[1, 2, 3], base=1, basis=Polynomial(degree=2))},
    ).fit(X, y)
    with pytest.raises(MonitoringSnapshotUnsupported, match="basis"):
        capture_monitoring_snapshot(_simple_bundle(model, X, y))
