"""SQL aggregate references retain native monitoring compatibility checks."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from superglm import Categorical, Numeric, OrderedCategorical, Spline, SuperGLM, collapse_levels

from pricing_pipeline.data.transforms import Log
from pricing_pipeline.modeling.monitoring import MonitoringError, MonitoringVariant
from pricing_pipeline.modeling.monitoring.contracts import _canonical_json
from pricing_pipeline.modeling.monitoring.data_checks import (
    MonitoringDataError,
    _require_compatible_monitoring_data,
    check_monitoring_data,
)
from pricing_pipeline.publishing.metadata import OffsetExportContract


def _snapshot(model, frame, weights=None, transforms=None):
    from pricing_pipeline.modeling.monitoring.snapshot import (
        capture_monitoring_snapshot,
        restore_monitoring_snapshot,
    )

    bundle = SimpleNamespace(
        fitted_model=model,
        X=frame,
        y=np.ones(len(frame)),
        sample_weight=weights,
        offset_contract=OffsetExportContract(handling="NONE"),
        fit_sample_weight_name="weight" if weights is not None else None,
        export_weight_name=None,
        input_transforms=transforms,
        model_name="preflight",
        model_version="1",
        export_id="export",
        manifest_id="manifest",
        split_set_id=None,
        row_order_sha256="a" * 64,
        model_source_sha256="b" * 64,
        model_frame_sha256="c" * 64,
    )
    saved = capture_monitoring_snapshot(bundle)
    return restore_monitoring_snapshot(saved.snapshot_json, expected_sha256=saved.snapshot_sha256)


@pytest.fixture(scope="module")
def mixed_case():
    frame = pd.DataFrame(
        {
            "segment": np.tile(["A", "B", "C", "D"], 60),
            "band": np.tile(["1", "2", "3", "4", "5", "6", "7", "8", "NA", "NA"], 24),
            "x": np.linspace(0, 100, 240),
            "log_amount": np.linspace(1, 3, 240),
        }
    )
    weights = np.where(frame.segment == "A", 2.0, 1.0)
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "segment": Categorical(
                grouping=collapse_levels(frame.segment, groups={"AB": ["A", "B"]}), base="AB"
            ),
            "band": OrderedCategorical(
                values={str(i): float(i) for i in range(1, 9)},
                specials=["NA"],
                grouping=collapse_levels(frame.band, groups={"middle": ["4", "5"]}),
                basis=Spline(kind="cr", k=3),
                base="1",
            ),
            "x": Spline(kind="cr", knots=[25, 50, 75]),
            "log_amount": Numeric(),
        },
    ).fit_reml(
        frame,
        np.random.default_rng(273).poisson(2, len(frame)),
        sample_weight=weights,
        max_reml_iter=5,
        runtime_validation="skip",
    )
    return (
        model,
        frame,
        weights,
        _snapshot(model, frame, weights, transforms={"log_amount": Log("amount").to_dict()}),
    )


def _assert_parity(model, baseline, reference, changed, weights, current_weights, variant):
    native = check_monitoring_data(
        model,
        changed,
        sample_weight=current_weights,
        reference_df=reference,
        reference_sample_weight=weights if current_weights is not None else None,
        variant=variant,
    )
    saved = check_monitoring_data(baseline, changed, sample_weight=current_weights, variant=variant)
    assert saved.reference_source == "sql_baseline"
    pd.testing.assert_frame_equal(saved.issues, native.issues)
    pd.testing.assert_frame_equal(saved.distributions, native.distributions)
    pd.testing.assert_frame_equal(saved.drift, native.drift)
    return saved


@pytest.mark.parametrize("variant", list(MonitoringVariant))
@pytest.mark.parametrize(
    "change",
    [
        "same",
        "mix",
        "unknown",
        "missing_group",
        "missing_member",
        "only_specials",
        "zero_group",
        "constant",
        "disjoint",
        "half_range",
    ],
)
def test_sql_preflight_matches_native_domains(mixed_case, change, variant):
    model, reference, weights, baseline = mixed_case
    changed = reference.copy()
    if change == "mix":
        changed["segment"] = "B"
    elif change == "unknown":
        changed.loc[0, "segment"] = "AB"
    elif change == "missing_group":
        changed = changed.loc[~changed.band.isin(["4", "5"])]
    elif change == "missing_member":
        changed = changed.loc[changed.band != "4"]
    elif change == "only_specials":
        changed = changed.loc[changed.band == "NA"]
    elif change == "constant":
        changed["log_amount"] = 2.0
    elif change == "disjoint":
        changed["x"] += 200
    elif change == "half_range":
        changed["x"] = 50 + changed.x / 2
    current_weights = weights[changed.index].copy()
    if change == "zero_group":
        current_weights[changed.band.isin(["4", "5"])] = 0
    report = _assert_parity(model, baseline, reference, changed, weights, current_weights, variant)
    if change in {"missing_group", "zero_group"} and variant is not MonitoringVariant.STATIC_SCORE:
        assert "MISSING_ORDERED_SUPPORT" in set(report.issues.code)
    if change == "mix":
        assert report.drift.query("feature == 'segment'").iloc[0].row_distance == pytest.approx(
            0.75
        )


def test_sql_reference_is_immutable_and_cannot_be_overridden(mixed_case, monkeypatch):
    model, reference, weights, baseline = mixed_case
    payload = baseline.payload()
    payload["reference_profiles"].clear()
    monkeypatch.setattr(SuperGLM, "fit_reml", lambda *a, **k: pytest.fail("preflight fitted"))
    report = _assert_parity(model, baseline, reference, reference, weights, None, "FROZEN_REFIT")
    assert set(report.distributions.feature) == {"segment", "band"}
    assert report.drift.row_distance.eq(0).all()
    for kwargs in ({"reference_df": reference}, {"reference_sample_weight": weights}):
        with pytest.raises(ValueError, match="reference.*cannot be overridden"):
            check_monitoring_data(baseline, reference, **kwargs)


def test_sql_mandatory_preflight_blocks_missing_ordered_group(mixed_case):
    _, reference, _, baseline = mixed_case
    changed = reference.loc[~reference.band.isin(["4", "5"])]
    with pytest.raises(MonitoringDataError, match="middle"):
        _require_compatible_monitoring_data(
            baseline, changed, None, variant=MonitoringVariant.FROZEN_REFIT
        )


def test_sql_preflight_rejects_changed_saved_reference_before_comparing(mixed_case):
    _, reference, _, baseline = mixed_case
    payload = baseline.payload()
    first = next(iter(payload["reference_profiles"]["segment"].values()))
    first["row_share"] = 0.9
    changed = replace(baseline, snapshot_json=_canonical_json(payload))
    with pytest.raises(MonitoringError, match="digest"):
        check_monitoring_data(changed, reference)


@pytest.mark.parametrize("special", [9, "NA"])
def test_sql_ordered_numeric_aliases_keep_saved_support_and_profiles(special):
    frame = pd.DataFrame({"band": np.tile(np.array([1, 2, 3, special], dtype=object), 40)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "band": OrderedCategorical(order=[1, 2, 3], specials=[special], basis=Spline("ps", k=5))
        },
    ).fit_reml(frame, np.tile([1, 2, 3, 2], 40), runtime_validation="skip", max_reml_iter=5)
    baseline = _snapshot(model, frame)
    report = _assert_parity(model, baseline, frame, frame.astype(str), None, None, "FROZEN_REFIT")
    assert report.compatible
    assert len(report.distributions) == 4
    assert report.drift.iloc[0].row_distance == 0


def test_sql_typed_categorical_levels_keep_distinct_distribution_rows():
    frame = pd.DataFrame({"segment": np.tile(np.array([1, "1", "base"], dtype=object), 40)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="base")},
    ).fit_reml(frame, np.tile([1, 2, 3], 40), runtime_validation="skip")
    baseline = _snapshot(model, frame)
    report = _assert_parity(model, baseline, frame, frame, None, None, "FROZEN_REFIT")
    assert len(report.distributions) == 3
    assert report.distributions.level_key.is_unique


@pytest.mark.parametrize("weighted_reference", [False, True])
def test_sql_weight_reference_presence_matches_candidate_semantics(weighted_reference):
    frame = pd.DataFrame({"segment": ["A", "B"] * 40})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="A")},
    ).fit_reml(frame, np.tile([1, 2], 40), runtime_validation="skip")
    reference_weights = np.ones(len(frame)) if weighted_reference else None
    baseline = _snapshot(model, frame, reference_weights)
    weights = np.where(frame.segment == "B", 9.0, 1.0)
    report = _assert_parity(
        model, baseline, frame, frame, reference_weights, weights, "FROZEN_REFIT"
    )
    assert ("WEIGHT_REFERENCE_UNAVAILABLE" in set(report.issues.code)) != weighted_reference
    if weighted_reference:
        assert report.drift.iloc[0].weight_distance == pytest.approx(0.4)
    else:
        assert pd.isna(report.drift.iloc[0].weight_distance)


@pytest.mark.parametrize("variant", list(MonitoringVariant))
def test_sql_static_unknown_base_fallback_remains_a_warning(variant):
    frame = pd.DataFrame({"segment": ["A", "B"] * 40})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="A", unseen="base")},
    ).fit_reml(frame, np.tile([1, 2], 40), runtime_validation="skip")
    baseline = _snapshot(model, frame)
    changed = frame.copy()
    changed.loc[0, "segment"] = "new"
    report = _assert_parity(model, baseline, frame, changed, None, None, variant)
    assert report.compatible == (variant is MonitoringVariant.STATIC_SCORE)
    assert report.issues.iloc[0].code == "UNKNOWN_LEVELS"


@pytest.mark.parametrize("policy", ["clip", "extend", "error"])
@pytest.mark.parametrize("variant", list(MonitoringVariant))
def test_sql_spline_boundaries_include_zero_weight_outliers(policy, variant):
    frame = pd.DataFrame({"x": np.linspace(0, 100, 160)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": Spline(kind="cr", k=5, extrapolation=policy)},
    ).fit_reml(
        frame,
        np.random.default_rng(482).poisson(2, len(frame)),
        runtime_validation="skip",
        max_reml_iter=5,
    )
    baseline = _snapshot(model, frame, np.ones(len(frame)))
    changed = frame.copy()
    changed.loc[0, "x"] = 200
    weights = np.ones(len(frame))
    weights[0] = 0
    report = _assert_parity(model, baseline, frame, changed, np.ones(len(frame)), weights, variant)
    issue = report.issues.query("code == 'SPLINE_OUT_OF_BOUNDS'").iloc[0]
    assert issue.affected_rows == 1
    assert issue.affected_weight == 0
    assert report.compatible == (policy != "error")


@pytest.mark.parametrize("case", ["null", "infinite", "missing", "empty", "weights"])
def test_sql_invalid_monitoring_inputs_retain_native_reports(mixed_case, case):
    model, reference, weights, baseline = mixed_case
    changed = reference.copy()
    current_weights = weights.copy()
    if case == "null":
        changed.loc[0, "band"] = None
    elif case == "infinite":
        changed.loc[0, "log_amount"] = np.inf
    elif case == "missing":
        changed = changed.drop(columns="log_amount")
    elif case == "empty":
        changed, current_weights = changed.iloc[:0], current_weights[:0]
    else:
        current_weights[:] = 0
    report = _assert_parity(
        model, baseline, reference, changed, weights, current_weights, "FROZEN_REFIT"
    )
    assert not report.compatible
