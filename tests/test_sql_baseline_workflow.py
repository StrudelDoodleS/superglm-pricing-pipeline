"""A SQL snapshot must retain the native monitoring rules and evidence."""

import json
from dataclasses import replace

import numpy as np
import pytest

from pricing_pipeline.modeling.monitoring import (
    MonitoringError,
    MonitoringVariant,
    run_monitoring_fit,
)
from pricing_pipeline.modeling.monitoring.snapshot import (
    capture_monitoring_snapshot,
    restore_monitoring_snapshot,
)
from tests.test_model_monitoring import _monitoring_candidate, monitoring_case  # noqa: F401


@pytest.fixture(scope="module")
def sql_case(monitoring_case, tmp_path_factory):  # noqa: F811 - imported pytest fixture
    model, df, y = monitoring_case
    candidate = _monitoring_candidate(tmp_path_factory.mktemp("sql-workflow"), model, df, y)
    snapshot = capture_monitoring_snapshot(candidate.bundle)
    baseline = restore_monitoring_snapshot(
        snapshot.snapshot_json, expected_sha256=snapshot.snapshot_sha256
    )
    return baseline, model, df, y


@pytest.mark.parametrize("variant", list(MonitoringVariant))
def test_snapshot_workflow_matches_native_monitoring(sql_case, variant):
    baseline, model, df, y = sql_case
    options = {
        "variant": variant,
        "continuous_points": 9,
        "max_reml_iter": 5,
        "runtime_validation": "skip",
    }
    expected = run_monitoring_fit(model, df, y, **options)
    actual = run_monitoring_fit(baseline, df, y, **options)

    np.testing.assert_allclose(
        actual.fitted_model.predict(df), expected.fitted_model.predict(df), rtol=1e-9
    )
    assert actual.contract == expected.contract
    assert actual.metrics == pytest.approx(expected.metrics, rel=1e-9, abs=1e-10)
    assert actual.lambdas == expected.lambdas
    assert [r.point_key for r in actual.relativities] == [
        r.point_key for r in expected.relativities
    ]
    np.testing.assert_allclose(
        [r.relativity for r in actual.relativities],
        [r.relativity for r in expected.relativities],
        rtol=1e-9,
    )
    assert actual.invariant_evidence.status == "VERIFIED"
    evidence = actual.invariant_evidence.payload()
    assert evidence["geometry"] == expected.invariant_evidence.payload()["geometry"]
    assert evidence["structure"] == expected.invariant_evidence.payload()["structure"]
    assert evidence["lambdas"] == expected.invariant_evidence.payload()["lambdas"]


def test_snapshot_workflow_rechecks_snapshot_digest(sql_case):
    baseline, _, df, y = sql_case
    damaged = replace(baseline, snapshot_json=baseline.snapshot_json + " ")
    with pytest.raises(MonitoringError, match="digest|canonical|SHA|hash"):
        run_monitoring_fit(damaged, df, y, variant="STATIC_SCORE")


def test_snapshot_workflow_binds_sql_identity(sql_case):
    baseline, _, df, y = sql_case
    identity = {"snapshot_sha256": baseline.snapshot_sha256, "model_run_id": 23}
    result = run_monitoring_fit(replace(baseline, identity=identity), df, y, variant="STATIC_SCORE")
    assert json.loads(result.fit_configuration_json)["baseline"] == identity


@pytest.mark.parametrize("identity", [{"snapshot_sha256": "0" * 64}, {}])
def test_snapshot_workflow_rejects_identity_from_another_snapshot(sql_case, identity):
    baseline, _, df, y = sql_case
    with pytest.raises(MonitoringError, match="snapshot.*identity|identity.*snapshot"):
        run_monitoring_fit(replace(baseline, identity=identity), df, y, variant="STATIC_SCORE")
