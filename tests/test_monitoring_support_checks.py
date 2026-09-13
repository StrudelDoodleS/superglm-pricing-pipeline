"""Stop unsupported refits before REML while preserving valid static scoring."""

import json

import numpy as np
import pandas as pd
import pytest
from superglm import Numeric, OrderedCategorical, Spline, SuperGLM, collapse_levels

from pricing_pipeline.modeling.monitoring import MonitoringVariant, run_monitoring_fit
from pricing_pipeline.modeling.monitoring.data_checks import (
    MonitoringDataError,
    check_monitoring_data,
)


@pytest.fixture(scope="module")
def continuous_case():
    df = pd.DataFrame({"x": np.linspace(0, 100, 401)})
    y = np.random.default_rng(137).poisson(np.exp(df.x / 200))
    model = SuperGLM(
        family="poisson", selection_penalty=0.0, features={"x": Spline(kind="cr", k=5)}
    ).fit_reml(df, y, max_reml_iter=5, runtime_validation="skip")
    return model, df, y


@pytest.fixture(scope="module")
def ordered_case():
    df = pd.DataFrame({"band": np.tile(["1", "2", "3", "4", "5", "6", "7", "8", "NA"], 40)})
    grouping = collapse_levels(df.band, groups={"middle": ["4", "5"]})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "band": OrderedCategorical(
                values={str(i): float(i) for i in range(1, 9)},
                specials=["NA"],
                grouping=grouping,
                basis=Spline(kind="cr", k=3),
                base="1",
            )
        },
    ).fit_reml(
        df,
        np.random.default_rng(138).poisson(2, len(df)),
        max_reml_iter=5,
        runtime_validation="skip",
    )
    return model, df


def test_complete_spline_support_needs_no_review(continuous_case, ordered_case):
    for model, df in (continuous_case[:2], ordered_case):
        report = check_monitoring_data(model, df, reference_df=df)
        assert report.compatible
        assert not report.needs_review


@pytest.mark.parametrize("variant", list(MonitoringVariant)[1:])
def test_disjoint_continuous_support_blocks_every_refit(continuous_case, variant):
    model, df, _ = continuous_case
    report = check_monitoring_data(model, df.assign(x=df.x + 200), variant=variant)
    assert not report.compatible
    assert "NO_SPLINE_OVERLAP" in set(report.issues.code)
    with pytest.raises(MonitoringDataError, match="x"):
        report.raise_for_errors()


def test_half_range_reports_lost_tail_without_rejecting_the_snapshot(continuous_case):
    model, df, _ = continuous_case
    report = check_monitoring_data(model, df.assign(x=50 + df.x / 2), reference_df=df)
    assert report.compatible
    assert "SPLINE_RANGE_LOSS" in set(report.issues.code)


def test_internal_empty_knot_interval_is_reported(continuous_case):
    model, df, _ = continuous_case
    changed = df.loc[(df.x < 25) | (df.x > 75)]
    report = check_monitoring_data(model, changed, reference_df=df)
    assert report.compatible
    assert "EMPTY_SPLINE_INTERVALS" in set(report.issues.code)


@pytest.mark.parametrize("zero_weight", [False, True])
def test_constant_effective_numeric_values_block_refit(zero_weight):
    df = pd.DataFrame({"x": np.linspace(0, 1, 80)})
    model = SuperGLM(family="poisson", features={"x": Numeric()}, selection_penalty=0).fit_reml(
        df, np.tile([1, 2], 40), runtime_validation="skip"
    )
    changed = df if zero_weight else df.assign(x=0.5)
    weights = np.r_[1.0, np.zeros(79)] if zero_weight else None
    report = check_monitoring_data(model, changed, sample_weight=weights)
    assert not report.compatible
    assert "CONSTANT_FEATURE" in set(report.issues.code)


def test_clipping_can_destroy_variation_even_when_raw_values_vary(continuous_case):
    model, df, _ = continuous_case
    changed = df.assign(x=100 + df.x)
    report = check_monitoring_data(model, changed)
    assert not report.compatible
    assert "CONSTANT_SPLINE" in set(report.issues.code)


def test_zero_weight_rows_do_not_supply_spline_overlap(continuous_case):
    model, df, _ = continuous_case
    changed = pd.concat([df, df.assign(x=df.x + 200)], ignore_index=True)
    weights = np.r_[np.zeros(len(df)), np.ones(len(df))]
    report = check_monitoring_data(model, changed, sample_weight=weights)
    assert not report.compatible
    assert "NO_SPLINE_OVERLAP" in set(report.issues.code)


@pytest.mark.parametrize("policy", ["clip", "extend", "error"])
def test_boundary_policy_and_affected_counts(continuous_case, policy):
    _, df, y = continuous_case
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": Spline(kind="cr", k=5, extrapolation=policy)},
    ).fit_reml(df, y, max_reml_iter=5, runtime_validation="skip")
    changed = df.copy()
    changed.loc[:4, "x"] = 120
    report = check_monitoring_data(model, changed, sample_weight=np.full(len(df), 2.0))
    issue = report.issues.query("code == 'SPLINE_OUT_OF_BOUNDS'").iloc[0]
    assert issue.severity == ("error" if policy == "error" else "warning")
    assert issue.affected_rows == 5
    assert issue.affected_weight == 10
    assert report.compatible == (policy != "error")


@pytest.mark.parametrize("missing", [["4", "5"], ["1"], ["8"]])
@pytest.mark.parametrize("variant", list(MonitoringVariant)[1:])
def test_missing_entire_ordered_group_blocks_refit(ordered_case, missing, variant):
    model, df = ordered_case
    changed = df.loc[~df.band.isin(missing)]
    report = check_monitoring_data(model, changed, reference_df=df, variant=variant)
    assert not report.compatible
    issue = report.issues.query("code == 'MISSING_ORDERED_SUPPORT'").iloc[0]
    assert issue.feature == "band"
    if missing == ["4", "5"]:
        assert "middle" in issue.message


def test_missing_one_group_member_is_only_a_warning(ordered_case):
    model, df = ordered_case
    report = check_monitoring_data(model, df.loc[df.band != "4"], reference_df=df)
    assert report.compatible
    assert "ABSENT_LEVELS" in set(report.issues.code)
    assert "MISSING_ORDERED_SUPPORT" not in set(report.issues.code)


def test_zero_weight_ordered_group_is_unsupported(ordered_case):
    model, df = ordered_case
    weights = np.where(df.band.isin(["4", "5"]), 0.0, 1.0)
    report = check_monitoring_data(model, df, sample_weight=weights)
    assert not report.compatible
    assert "MISSING_ORDERED_SUPPORT" in set(report.issues.code)


def test_missing_special_is_not_a_missing_smooth_group(ordered_case):
    model, df = ordered_case
    report = check_monitoring_data(model, df.loc[df.band != "NA"], reference_df=df)
    assert report.compatible
    assert "MISSING_ORDERED_SUPPORT" not in set(report.issues.code)


def test_only_special_rows_cannot_refit_a_smooth(ordered_case):
    model, df = ordered_case
    report = check_monitoring_data(model, df.loc[df.band == "NA"])
    assert not report.compatible
    assert "MISSING_ORDERED_SUPPORT" in set(report.issues.code)


@pytest.mark.parametrize("variant", list(MonitoringVariant)[1:])
def test_direct_monitoring_blocks_before_any_refit(continuous_case, monkeypatch, variant):
    model, df, y = continuous_case
    monkeypatch.setattr(SuperGLM, "fit_reml", lambda *a, **k: pytest.fail("REML started"))
    with pytest.raises(MonitoringDataError) as error:
        run_monitoring_fit(model, df.assign(x=df.x + 200), y, variant=variant)
    assert "NO_SPLINE_OVERLAP" in set(error.value.report.issues.code)


def test_static_scoring_does_not_require_refit_support(continuous_case, ordered_case):
    model, df, y = continuous_case
    changed = df.assign(x=df.x + 200)
    report = check_monitoring_data(model, changed, variant="STATIC_SCORE")
    assert report.compatible
    result = run_monitoring_fit(model, changed, y, variant="STATIC_SCORE", continuous_points=11)
    assert result.variant is MonitoringVariant.STATIC_SCORE
    model, df = ordered_case
    changed = df.loc[df.band == "NA"]
    assert check_monitoring_data(model, changed, variant="STATIC_SCORE").compatible


def test_reports_collect_multiple_degenerate_features_and_serialize():
    df = pd.DataFrame({"a": np.linspace(0, 1, 80), "b": np.tile([0, 1], 40)})
    model = SuperGLM(
        family="poisson", features={"a": Numeric(), "b": Numeric()}, selection_penalty=0
    ).fit_reml(df, np.tile([1, 2], 40), runtime_validation="skip")
    report = check_monitoring_data(model, df.assign(a=1, b=0))
    assert set(report.issues.query("severity == 'error'").feature) == {"a", "b"}
    assert json.loads(report.to_json())["compatible"] is False


def test_adaptive_refit_rejects_declared_knots_outside_new_domain(continuous_case):
    _, df, y = continuous_case
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": Spline(kind="cr", knots=[25, 50, 75])},
    ).fit_reml(df, y, max_reml_iter=5, runtime_validation="skip")
    changed = df.assign(x=50 + df.x / 2)
    assert check_monitoring_data(model, changed, variant="FROZEN_REFIT").compatible
    report = check_monitoring_data(model, changed, variant="FULL_ADAPTIVE")
    assert not report.compatible
    assert "SPLINE_KNOTS_OUT_OF_BOUNDS" in set(report.issues.code)


@pytest.mark.parametrize("explicit_boundary", [False, True])
def test_adaptive_boundary_check_respects_declared_geometry(continuous_case, explicit_boundary):
    _, df, y = continuous_case
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "x": Spline(
                kind="cr",
                k=5,
                extrapolation="error",
                boundary=(0, 100) if explicit_boundary else None,
            )
        },
    ).fit_reml(df, y, max_reml_iter=5, runtime_validation="skip")
    changed = df.assign(x=df.x * 1.1)
    report = check_monitoring_data(model, changed, variant="FULL_ADAPTIVE")
    assert report.compatible == (not explicit_boundary)
    assert ("SPLINE_OUT_OF_BOUNDS" in set(report.issues.code)) == explicit_boundary


def test_boundary_error_includes_zero_weight_rows_and_matches_roundoff_tolerance(continuous_case):
    _, df, y = continuous_case
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": Spline(kind="cr", k=5, extrapolation="error")},
    ).fit_reml(df, y, max_reml_iter=5, runtime_validation="skip")
    changed = df.copy()
    changed.loc[0, "x"] = -1e-12
    assert check_monitoring_data(model, changed).compatible
    changed.loc[0, "x"] = -1
    weights = np.ones(len(df))
    weights[0] = 0
    report = check_monitoring_data(model, changed, sample_weight=weights)
    assert not report.compatible
    assert report.issues.query("code == 'SPLINE_OUT_OF_BOUNDS'").iloc[0].affected_weight == 0


def test_ordered_group_failure_stops_direct_refit(ordered_case, monkeypatch):
    model, df = ordered_case
    changed = df.loc[~df.band.isin(["4", "5"])]
    monkeypatch.setattr(SuperGLM, "fit_reml", lambda *a, **k: pytest.fail("REML started"))
    with pytest.raises(MonitoringDataError, match="middle"):
        run_monitoring_fit(model, changed, np.ones(len(changed)), variant="FROZEN_REFIT")


def test_zero_weight_ordered_rows_still_obey_prediction_boundaries():
    df = pd.DataFrame({"band": np.tile(["1", "2", "3", "4", "NA"], 40)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "band": OrderedCategorical(
                order=[str(i) for i in range(1, 9)],
                specials=["NA"],
                basis=Spline(kind="cr", k=3, extrapolation="error"),
            )
        },
    ).fit_reml(df, np.random.default_rng(139).poisson(2, len(df)), runtime_validation="skip")
    changed = pd.DataFrame({"band": ["8", "NA"]})
    report = check_monitoring_data(model, changed, sample_weight=[0, 1], variant="STATIC_SCORE")
    assert not report.compatible
    issue = report.issues.query("code == 'SPLINE_OUT_OF_BOUNDS'").iloc[0]
    assert issue.affected_rows == 1
    assert issue.affected_weight == 0
    with pytest.raises(MonitoringDataError):
        run_monitoring_fit(model, changed, [1, 1], sample_weight=[0, 1], variant="STATIC_SCORE")


def test_adaptive_numeric_boundary_still_checks_zero_weight_outliers(continuous_case):
    _, df, y = continuous_case
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"x": Spline(kind="cr", k=5, extrapolation="error")},
    ).fit_reml(df, y, max_reml_iter=5, runtime_validation="skip")
    changed = df.copy()
    changed.loc[0, "x"] = 200
    weights = np.ones(len(df))
    weights[0] = 0
    report = check_monitoring_data(model, changed, sample_weight=weights, variant="FULL_ADAPTIVE")
    assert not report.compatible
    assert "SPLINE_OUT_OF_BOUNDS" in set(report.issues.code)
    with pytest.raises(MonitoringDataError):
        run_monitoring_fit(model, changed, y, sample_weight=weights, variant="FULL_ADAPTIVE")
