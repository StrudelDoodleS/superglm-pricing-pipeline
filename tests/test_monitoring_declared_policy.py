"""Promoting a controlled refit preserves the declared policy for later epochs."""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from superglm import OrderedCategorical, Spline, SuperGLM
from superglm.types import LambdaPolicy

from pricing_pipeline.modeling.monitoring import (
    MonitoringError,
    MonitoringVariant,
    run_monitoring_fit,
)
from pricing_pipeline.modeling.monitoring.contracts import _canonical_json, _sha256_text
from pricing_pipeline.modeling.monitoring.data_checks import check_monitoring_data
from pricing_pipeline.modeling.monitoring.snapshot import (
    MonitoringSnapshotUnsupported,
    capture_monitoring_snapshot,
    restore_monitoring_snapshot,
)
from pricing_pipeline.modeling.recipes.schema import RecipeCapture
from pricing_pipeline.publishing.metadata import OffsetExportContract


def _bundle(model, X, y):
    return SimpleNamespace(
        fitted_model=model,
        X=X,
        y=y,
        sample_weight=None,
        offset_contract=OffsetExportContract(handling="NONE"),
        fit_sample_weight_name=None,
        export_weight_name=None,
        input_transforms=None,
        model_name="policy_test",
        model_version="v1",
        export_id="policy_export",
        manifest_id="policy_manifest",
        split_set_id=None,
        row_order_sha256="a" * 64,
        model_source_sha256="b" * 64,
        model_frame_sha256="c" * 64,
    )


def _restore(payload):
    encoded = _canonical_json(payload)
    return restore_monitoring_snapshot(encoded, expected_sha256=_sha256_text(encoded))


def _capture(model, X, y, **kwargs):
    captured = capture_monitoring_snapshot(_bundle(model, X, y), **kwargs)
    return restore_monitoring_snapshot(
        captured.snapshot_json, expected_sha256=captured.snapshot_sha256
    )


@pytest.fixture(scope="module")
def baseline_case():
    rng = np.random.default_rng(812)
    n = 240
    X = pd.DataFrame(
        {
            "learned": np.linspace(0.0, 1.0, n),
            "governed": rng.uniform(0.0, 1.0, n),
            "ordered": np.resize(["A", "B", "C", "D", "E"], n),
        }
    )
    y = rng.poisson(np.exp(0.3 + np.sin(X.learned * 5) + 0.2 * X.governed))
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "learned": Spline("cr", k=4),
            "governed": Spline(
                "cr",
                knots=[0.2, 0.4, 0.6, 0.8],
                boundary=(0.0, 1.0),
                lambda_policy=LambdaPolicy.fixed(0.75),
            ),
            "ordered": OrderedCategorical(
                order=["A", "B", "C", "D", "E"],
                base="A",
                basis=Spline("cr", k=3),
            ),
        },
    ).fit_reml(X, y, max_reml_iter=5, runtime_validation="skip")
    return _capture(model, X, y), X, y


@pytest.mark.parametrize("promoted_variant", ["FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"])
def test_promoted_refit_keeps_declared_controls_for_two_more_epochs(
    baseline_case, promoted_variant
):
    baseline, original_X, y = baseline_case
    expected_governed_knots = baseline.term_metadata["governed"]["fitted"]["knots"]
    for epoch in (1, 2):
        X = original_X.copy()
        X["learned"] = 0.1 * epoch + original_X.learned * (1.0 - 0.2 * epoch)
        refit = run_monitoring_fit(
            baseline,
            X,
            y,
            variant=promoted_variant,
            max_reml_iter=5,
            runtime_validation="skip",
        )
        baseline = _capture(
            refit.fitted_model,
            X,
            y,
            declared_monitoring_policy=baseline.declared_monitoring_policy,
        )
        np.testing.assert_allclose(
            baseline.predict(X), refit.fitted_model.predict(X), rtol=1e-10, atol=1e-11
        )
        adaptive = run_monitoring_fit(
            baseline,
            original_X,
            y,
            variant="FULL_ADAPTIVE",
            max_reml_iter=5,
            runtime_validation="skip",
        )
        geometry = adaptive.invariant_evidence.payload()["geometry"]
        assert geometry["protected_fields"] == ["governed.boundary", "governed.knots"]
        assert geometry["fitted"]["learned"]["boundary"] == [0.0, 1.0]
        assert geometry["fitted"]["governed"]["knots"] == expected_governed_knots
        lambdas = {row.term_name: row for row in adaptive.lambdas}
        assert lambdas["learned"].lambda_mode == "ESTIMATED"
        assert lambdas["ordered"].lambda_mode == "ESTIMATED"
        assert lambdas["governed"].lambda_mode == "FIXED"
        assert lambdas["governed"].lambda_value == 0.75
        frozen = run_monitoring_fit(
            baseline, X, y, variant="FROZEN_REFIT", max_reml_iter=5, runtime_validation="skip"
        )
        assert {row.component_name: row.lambda_value for row in frozen.lambdas} == {
            row.component_name: row.lambda_value for row in baseline.lambdas
        }
        assert frozen.invariant_evidence.payload()["geometry"]["fitted"] == {
            name: {"knots": item["fitted"]["knots"], "boundary": item["fitted"]["boundary"]}
            for name, metadata in baseline.term_metadata.items()
            for item in [metadata.get("spline", metadata)]
        }
        if promoted_variant != "FULL_ADAPTIVE":
            # The saved execution remains explicit even though future policy is adaptive.
            assert baseline.payload()["recipe"]["features"]["learned"]["knots"] is not None
        if promoted_variant == "FROZEN_REFIT":
            execution_modes = {
                row["lambda_mode"] for row in baseline.payload()["fitted_lambda_policies"]
            }
            assert execution_modes == {"FIXED"}


def test_adaptive_preflight_uses_declared_geometry_after_promotion(baseline_case):
    baseline, X, y = baseline_case
    narrow = X.copy()
    narrow["learned"] = 0.2 + X.learned * 0.6
    refit = run_monitoring_fit(
        baseline, narrow, y, variant="FROZEN_REFIT", max_reml_iter=5, runtime_validation="skip"
    )
    promoted = _capture(
        refit.fitted_model,
        narrow,
        y,
        declared_monitoring_policy=baseline.declared_monitoring_policy,
    )
    expanded = X.copy()
    expanded["learned"] = -0.2 + X.learned * 1.4
    check = check_monitoring_data(promoted, expanded, variant="FULL_ADAPTIVE")
    check.raise_for_errors()
    assert "SPLINE_OUT_OF_BOUNDS" not in set(check.issues.code)


def test_v1_snapshot_can_supply_declared_policy_for_a_promoted_refit(baseline_case):
    baseline, X, y = baseline_case
    legacy_payload = baseline.payload()
    legacy_payload["schema_version"] = 1
    legacy_payload.pop("declared_monitoring_policy", None)
    legacy = _restore(legacy_payload)
    refit = run_monitoring_fit(
        legacy, X, y, variant="FROZEN_REFIT", max_reml_iter=5, runtime_validation="skip"
    )
    promoted = _capture(
        refit.fitted_model, X, y, declared_monitoring_policy=legacy.declared_monitoring_policy
    )
    assert promoted.declared_monitoring_policy["splines"]["learned"]["knots"] is None
    adaptive = promoted.materialize("FULL_ADAPTIVE")
    learned = dict(adaptive._config.feature_templates)["learned"]
    assert learned._explicit_knots is None
    assert learned._lambda_policy is None


@pytest.mark.parametrize("change", ["missing_spline", "extra_control", "invalid_policy"])
def test_snapshot_rejects_malformed_declared_controls(baseline_case, change):
    baseline, _, _ = baseline_case
    payload = baseline.payload()
    controls = payload["declared_monitoring_policy"]["splines"]
    if change == "missing_spline":
        controls.pop("ordered")
    elif change == "extra_control":
        controls["learned"]["degree"] = 1
    else:
        controls["learned"]["lambda_policy"] = {"mode": "invalid"}
    with pytest.raises(MonitoringError, match="policy|controls"):
        _restore(payload)


def test_declared_policy_access_does_not_mutate_saved_intent(baseline_case):
    baseline, _, _ = baseline_case
    original = baseline.snapshot_json
    exported = baseline.declared_monitoring_policy
    exported["splines"]["learned"]["knots"] = [0.1, 0.2]
    assert baseline.snapshot_json == original
    assert baseline.declared_monitoring_policy["splines"]["learned"]["knots"] is None


def test_mixed_component_lambda_policies_survive_consecutive_frozen_promotions():
    X = pd.DataFrame({"x": np.linspace(0.0, 1.0, 180)})
    y = np.random.default_rng(928).poisson(np.exp(0.2 + np.sin(X.x * 4)))
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "x": Spline(
                "cr",
                n_knots=4,
                m=(1, 2),
                lambda_policy={"d1": LambdaPolicy.estimate(), "d2": LambdaPolicy.fixed(0.5)},
            )
        },
    ).fit_reml(X, y, max_reml_iter=5, runtime_validation="skip")
    baseline = _capture(model, X, y)
    for _ in range(2):
        frozen = run_monitoring_fit(
            baseline, X, y, variant="FROZEN_REFIT", max_reml_iter=5, runtime_validation="skip"
        )
        baseline = _capture(
            frozen.fitted_model,
            X,
            y,
            declared_monitoring_policy=baseline.declared_monitoring_policy,
        )
        refit = run_monitoring_fit(
            baseline, X, y, variant="REESTIMATE_LAMBDA", max_reml_iter=5, runtime_validation="skip"
        )
        policies = {row.component_name: row for row in refit.lambdas}
        assert policies["x:d1"].lambda_mode == "ESTIMATED"
        assert policies["x:d2"].lambda_mode == "FIXED"
        assert policies["x:d2"].lambda_value == 0.5


def test_monitoring_publication_rejects_unavailable_challenger_snapshot(baseline_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import snapshot
    from pricing_pipeline.modeling.monitoring.storage import _save_captured_baseline

    baseline, X, y = baseline_case
    refit = run_monitoring_fit(
        baseline, X, y, variant="FROZEN_REFIT", max_reml_iter=5, runtime_validation="skip"
    )
    bundle = _bundle(refit.fitted_model, X, y)
    bundle.recipe_capture = RecipeCapture()
    source = {
        **baseline.payload()["bundle_identity"],
        "recipe_status": "LEGACY",
        "recipe_sha256": None,
    }

    def unsupported(bundle, *, declared_monitoring_policy):
        raise MonitoringSnapshotUnsupported("snapshot encoder cannot capture this refit")

    monkeypatch.setattr(snapshot, "capture_monitoring_snapshot", unsupported)
    with pytest.raises(MonitoringError, match="challenger SQL snapshot is unavailable"):
        _save_captured_baseline(
            None,
            source,
            bundle,
            created_by="test",
            monitoring_baseline=baseline,
            monitoring_variant=MonitoringVariant.FROZEN_REFIT,
        )
