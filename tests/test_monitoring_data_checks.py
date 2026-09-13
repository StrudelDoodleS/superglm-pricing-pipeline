"""Reject incompatible snapshots before refitting and expose categorical mix changes."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from superglm import Categorical, Numeric, OrderedCategorical, Spline, SuperGLM, collapse_levels

from pricing_pipeline.modeling.monitoring import MonitoringVariant, run_monitoring_fit
from pricing_pipeline.modeling.monitoring.data_checks import (
    MonitoringDataError,
    check_monitoring_data,
)


@pytest.fixture(scope="module")
def baseline_case():
    df = pd.DataFrame({"segment": ["low"] * 90 + ["high"] * 10, "age": np.arange(100) / 100})
    y = np.random.default_rng(17).poisson(1.5, len(df))
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="low"), "age": Numeric()},
    ).fit_reml(df, y, runtime_validation="skip")
    return model, df, y


def test_matching_snapshot_passes_without_fitting(baseline_case, monkeypatch):
    model, df, _ = baseline_case
    monkeypatch.setattr(SuperGLM, "fit_reml", lambda *a, **k: pytest.fail("preflight fitted"))
    report = check_monitoring_data(model, df, reference_df=df)
    assert report.compatible
    assert not report.needs_review
    assert report.drift.iloc[0].row_distance == 0
    report.raise_for_errors()
    assert json.loads(report.to_json())["compatible"] is True


def test_new_level_reports_counts_and_blocks(baseline_case):
    model, df, _ = baseline_case
    changed = df.copy()
    changed.loc[:3, "segment"] = "new"
    report = check_monitoring_data(model, changed, reference_df=df)
    unknown = report.issues.query("code == 'UNKNOWN_LEVELS'").iloc[0]
    assert unknown.feature == "segment"
    assert unknown.affected_rows == 4
    assert not report.compatible
    with pytest.raises(MonitoringDataError, match="segment") as exc:
        report.raise_for_errors()
    assert exc.value.report is report


@pytest.mark.parametrize("variant", list(MonitoringVariant))
def test_unknown_level_stops_before_contract_or_fit(baseline_case, monkeypatch, variant):
    from pricing_pipeline.modeling.monitoring import workflow

    model, df, y = baseline_case
    changed = df.copy()
    changed.loc[0, "segment"] = "new"
    monkeypatch.setattr(
        workflow, "build_model_fit_contract", lambda *a, **k: pytest.fail("too late")
    )
    monkeypatch.setattr(SuperGLM, "fit_reml", lambda *a, **k: pytest.fail("refit started"))
    with pytest.raises(MonitoringDataError, match="segment"):
        run_monitoring_fit(model, changed, y, variant=variant)


def test_missing_known_level_warns_without_blocking(baseline_case):
    model, df, _ = baseline_case
    report = check_monitoring_data(model, df.iloc[:90], reference_df=df)
    assert report.compatible
    assert report.needs_review
    absent = report.issues.query("code == 'ABSENT_LEVELS'").iloc[0]
    assert "high" in absent.message
    assert "support" in absent.message
    report.raise_for_errors()
    high = report.distributions.query("level == 'high'").iloc[0]
    assert high.current_rows == 0
    assert high.reference_rows == 10


def test_same_labels_with_changed_mix_trigger_review(baseline_case):
    model, df, _ = baseline_case
    changed = df.assign(segment=["low"] * 20 + ["high"] * 80)
    report = check_monitoring_data(model, changed, reference_df=df)
    assert report.compatible
    assert report.needs_review
    assert report.drift.iloc[0].row_distance == pytest.approx(0.7)
    assert "CATEGORICAL_DRIFT" in set(report.issues.code)
    assert "SQL" in report.issues.query("code == 'CATEGORICAL_DRIFT'").iloc[0].message
    report.raise_for_errors()
    assert not check_monitoring_data(
        model, changed, reference_df=df, drift_threshold=0.8
    ).needs_review


def test_weighted_mix_can_drift_with_identical_row_counts(baseline_case):
    model, df, _ = baseline_case
    current_weights = np.where(df.segment == "high", 81.0, 1.0)
    report = check_monitoring_data(
        model,
        df,
        reference_df=df,
        sample_weight=current_weights,
        reference_sample_weight=np.ones(len(df)),
    )
    assert report.drift.iloc[0].row_distance == 0
    assert report.drift.iloc[0].weight_distance == pytest.approx(0.8)
    assert report.needs_review


def test_missing_reference_is_explicit(baseline_case):
    model, df, _ = baseline_case
    report = check_monitoring_data(model, df)
    assert report.compatible
    assert report.drift.empty
    assert "REFERENCE_UNAVAILABLE" in set(report.issues.code)


def test_weights_are_not_compared_to_unweighted_reference(baseline_case):
    model, df, _ = baseline_case
    report = check_monitoring_data(model, df, reference_df=df, sample_weight=np.ones(len(df)))
    assert report.compatible
    assert pd.isna(report.drift.iloc[0].weight_distance)
    assert "WEIGHT_REFERENCE_UNAVAILABLE" in set(report.issues.code)


@pytest.mark.parametrize("threshold", [0, -1, 1.1, np.nan, np.inf, True, "bad"])
def test_drift_threshold_must_be_finite_fraction(baseline_case, threshold):
    model, df, _ = baseline_case
    with pytest.raises(ValueError, match="drift_threshold"):
        check_monitoring_data(model, df, drift_threshold=threshold)


@pytest.mark.parametrize(
    "case,code",
    [
        ("missing", "MISSING_FEATURE"),
        ("duplicate", "DUPLICATE_COLUMNS"),
        ("null", "INVALID_VALUES"),
        ("infinite", "INVALID_VALUES"),
        ("text_numeric", "INVALID_VALUES"),
        ("nested", "INVALID_VALUES"),
        ("empty", "EMPTY_DATA"),
    ],
)
def test_invalid_snapshot_is_reported(baseline_case, case, code):
    model, df, _ = baseline_case
    changed = df.copy()
    if case == "missing":
        changed = changed.drop(columns="age")
    elif case == "duplicate":
        changed = pd.concat([changed, changed[["age"]]], axis=1)
    elif case == "null":
        changed.loc[0, "segment"] = None
    elif case == "infinite":
        changed.loc[0, "age"] = np.inf
    elif case == "text_numeric":
        changed["age"] = "oops"
    elif case == "nested":
        changed.at[0, "segment"] = ["low"]
    else:
        changed = changed.iloc[:0]
    report = check_monitoring_data(model, changed, reference_df=df)
    assert not report.compatible
    assert code in set(report.issues.code)


@pytest.mark.parametrize(
    "weights", [[1], np.zeros(100), -np.ones(100), np.full(100, np.nan), np.ones((100, 1))]
)
def test_invalid_weights_block_preflight(baseline_case, weights):
    model, df, _ = baseline_case
    report = check_monitoring_data(model, df, sample_weight=weights, reference_df=df)
    assert not report.compatible
    assert "INVALID_WEIGHTS" in set(report.issues.code)


def test_grouping_checks_original_levels_and_preserves_raw_mix():
    df = pd.DataFrame({"segment": np.tile(["A", "B", "C"], 40)})
    grouping = collapse_levels(df.segment, groups={"AB": ["A", "B"]})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="AB", grouping=grouping)},
    ).fit_reml(df, np.tile([1, 2, 3], 40), runtime_validation="skip")
    changed = df.assign(segment=np.tile(["B", "B", "C"], 40))
    report = check_monitoring_data(model, changed, reference_df=df)
    assert report.compatible
    assert report.drift.iloc[0].row_distance == pytest.approx(1 / 3)
    assert set(report.distributions.level) == {"A", "B", "C"}
    bad = df.copy()
    bad.loc[0, "segment"] = "AB"
    assert not check_monitoring_data(model, bad, reference_df=df).compatible


def test_ordered_numeric_spellings_and_specials_are_valid():
    df = pd.DataFrame({"band": np.tile(np.array([1, 2, 3, "MISSING"], dtype=object), 40)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "band": OrderedCategorical(
                order=[1, 2, 3], specials=["MISSING"], basis=Spline(kind="ps", k=5)
            )
        },
    ).fit_reml(df, np.tile([1, 2, 3, 2], 40), runtime_validation="skip", max_reml_iter=5)
    changed = df.astype(str)
    report = check_monitoring_data(model, changed, reference_df=df)
    assert report.compatible
    assert not report.needs_review
    changed.loc[0, "band"] = "NEW"
    assert not check_monitoring_data(model, changed, reference_df=df).compatible


def test_static_base_fallback_is_preserved_but_preflight_for_refits_blocks(baseline_case):
    _, df, y = baseline_case
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="low", unseen="base"), "age": Numeric()},
    ).fit_reml(df, y, runtime_validation="skip")
    changed = df.copy()
    changed.loc[0, "segment"] = "new"
    assert not check_monitoring_data(model, changed, reference_df=df).compatible
    with pytest.warns(UserWarning, match="unseen"):
        result = run_monitoring_fit(model, changed, y, variant=MonitoringVariant.STATIC_SCORE)
    assert result.variant is MonitoringVariant.STATIC_SCORE


def test_candidate_uses_reverified_reference_not_mutable_caller_bundle(baseline_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import data_checks
    from pricing_pipeline.workbench.core import Candidate

    model, df, _ = baseline_case
    candidate = object.__new__(Candidate)
    candidate.bundle = SimpleNamespace(X=df.assign(segment="wrong"))
    verified = SimpleNamespace(X=df, sample_weight=None)
    calls = []

    def resolve(value):
        calls.append(value)
        return model, {"model_run_id": 1}, verified

    monkeypatch.setattr(data_checks, "_resolve_monitoring_baseline", resolve)
    report = check_monitoring_data(candidate, df)
    assert calls == [candidate]
    assert report.compatible
    assert not report.needs_review
    with pytest.raises(ValueError, match="reference"):
        check_monitoring_data(candidate, df, reference_df=df)


def test_categorical_numeric_and_text_levels_keep_distinct_profiles():
    df = pd.DataFrame({"segment": np.tile(np.array([1, "1", "base"], dtype=object), 40)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="base", levels=[1, "1", "base"])},
    ).fit_reml(df, np.tile([1, 2, 3], 40), runtime_validation="skip")
    report = check_monitoring_data(model, df, reference_df=df)
    assert report.compatible
    assert len(report.distributions) == 3
    assert report.distributions.level_key.is_unique
    assert report.drift.iloc[0].row_distance == 0


def test_zero_weight_level_has_no_effective_support(baseline_case):
    model, df, _ = baseline_case
    report = check_monitoring_data(
        model,
        df,
        reference_df=df,
        sample_weight=np.where(df.segment == "high", 0.0, 1.0),
        reference_sample_weight=np.ones(len(df)),
    )
    assert report.compatible
    assert "ABSENT_LEVELS" in set(report.issues.code)
    assert report.distributions.query("level == 'high'").iloc[0].current_weight == 0


def test_grouping_raw_level_without_a_fitted_group_is_rejected():
    declared = pd.Series(["A", "B", "C", "D"])
    grouping = collapse_levels(declared, groups={"AB": ["A", "B"]})
    df = pd.DataFrame({"segment": np.tile(["A", "B", "C"], 40)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={"segment": Categorical(base="AB", grouping=grouping)},
    ).fit_reml(df, np.tile([1, 2, 3], 40), runtime_validation="skip")
    changed = df.copy()
    changed.loc[0, "segment"] = "D"
    report = check_monitoring_data(model, changed, reference_df=df)
    assert not report.compatible
    assert "UNKNOWN_LEVELS" in set(report.issues.code)


def test_numeric_ordered_special_aliases_share_one_distribution_row():
    df = pd.DataFrame({"band": np.tile([1, 2, 3, 9], 40)})
    model = SuperGLM(
        family="poisson",
        selection_penalty=0.0,
        features={
            "band": OrderedCategorical(order=[1, 2, 3], specials=[9], basis=Spline(kind="ps", k=5))
        },
    ).fit_reml(df, np.tile([1, 2, 3, 2], 40), runtime_validation="skip", max_reml_iter=5)
    report = check_monitoring_data(model, df.astype(str), reference_df=df)
    assert report.compatible
    assert not report.needs_review
    assert len(report.distributions) == 4
    assert report.distributions.query("level == '9'").iloc[0].current_rows == 40


@pytest.mark.parametrize("weights", [np.ones(100, dtype=complex) * (1 + 3j), [10**500] * 100])
def test_nonreal_or_overflowing_weights_are_reported(baseline_case, weights):
    model, df, _ = baseline_case
    report = check_monitoring_data(model, df, sample_weight=weights, reference_df=df)
    assert not report.compatible
    assert "INVALID_WEIGHTS" in set(report.issues.code)


@pytest.mark.parametrize("representation", ["decimal", "string", "object"])
def test_numeric_representations_supported_by_superglm_remain_compatible(
    baseline_case, representation
):
    from decimal import Decimal

    model, df, _ = baseline_case
    changed = df.copy()
    if representation == "decimal":
        changed["age"] = changed.age.map(lambda value: Decimal(str(value)))
    else:
        changed["age"] = changed.age.astype(str if representation == "string" else object)
    assert np.allclose(model.predict(changed), model.predict(df))
    assert check_monitoring_data(model, changed, reference_df=df).compatible


@pytest.mark.parametrize("location", ["weight", "feature"])
def test_complex_numpy_scalars_inside_object_columns_are_rejected(baseline_case, location):
    model, df, _ = baseline_case
    values = np.array([np.complex128(1 + 3j)] * len(df), dtype=object)
    if location == "weight":
        report = check_monitoring_data(model, df, sample_weight=values, reference_df=df)
        expected = "INVALID_WEIGHTS"
    else:
        changed = df.assign(age=pd.Series(values, dtype=object))
        report = check_monitoring_data(model, changed, reference_df=df)
        expected = "INVALID_VALUES"
    assert not report.compatible
    assert expected in set(report.issues.code)
