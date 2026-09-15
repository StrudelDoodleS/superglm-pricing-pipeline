"""Publication and SQL lineage tests for recurring monitoring baselines."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from pricing_pipeline import notebook as api


def _deploy(pricing, saved):
    with pricing.engine.begin() as connection:
        # The offline mirror records local audit packages; emulate a remote
        # published/deployed package only within this SQL integration fixture.
        connection.execute(
            text(
                "UPDATE pricing.PRICING_RATE_PACKAGE SET package_status='PUBLISHED' WHERE rate_package_id=:package"
            ),
            {"package": saved.rate_package_id},
        )
        connection.execute(
            text("""INSERT INTO pricing.PRICING_MODEL_DEPLOYMENT
                (model_id, rate_package_id, deployment_slot, effective_from_ts, deployed_by)
                VALUES (:model, :package, 'PRODUCTION', CURRENT_TIMESTAMP, 'test')"""),
            {"model": saved.model_id, "package": saved.rate_package_id},
        )


def test_publication_captures_one_json_baseline_without_deploying(fitted_case):
    pricing, _, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    api.save_model_version(pricing, candidate)
    with pricing.engine.connect() as connection:
        row = (
            connection.execute(text("SELECT * FROM pricing.MODEL_MONITORING_BASELINE"))
            .mappings()
            .one()
        )
        assert str(row["model_run_id"]) == str(saved.model_run_id)
        assert row["rate_package_id"] == saved.rate_package_id
        assert row["capture_status"] == "CAPTURED"
        assert hashlib.sha256(row["snapshot_json"].encode()).hexdigest() == row["snapshot_sha256"]
        lineage = json.loads(row["source_lineage_json"])
        assert lineage["recipe_sha256"] == candidate.recipe.sha256
        assert lineage["publication_receipt_sha256"] == saved.publication_receipt_sha256
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.PRICING_MODEL_DEPLOYMENT")
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE pricing.MODEL_MONITORING_BASELINE SET snapshot_json='{}'",
        "DELETE FROM pricing.MODEL_MONITORING_BASELINE",
        "UPDATE pricing.MODEL_RUN SET publication_receipt_sha256='changed'",
        "UPDATE pricing.PRICING_RATE_PACKAGE SET publication_receipt_sha256='changed'",
    ],
)
def test_published_monitoring_state_and_source_identity_are_immutable(fitted_case, statement):
    pricing, _, candidate, _ = fitted_case
    api.save_model_version(pricing, candidate)
    with pytest.raises(IntegrityError), pricing.engine.begin() as connection:
        connection.execute(text(statement))


def test_sql_loader_does_not_read_candidate_files(fitted_case):
    from pricing_pipeline.modeling.monitoring.storage import load_monitoring_baseline

    pricing, _, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    _deploy(pricing, saved)
    build = candidate.completed_build
    for filename in (
        build.candidate_artifact_path,
        build.rating_workbook_path,
        build.publication_receipt_path,
    ):
        Path(filename).unlink()
    baseline = load_monitoring_baseline(pricing.engine, saved.model_name)
    assert str(baseline.identity["model_run_id"]) == str(saved.model_run_id)
    assert baseline.identity["rate_package_id"] == saved.rate_package_id
    assert baseline.identity["snapshot_sha256"] == baseline.snapshot_sha256
    assert (
        api.load_monitoring_baseline(pricing, model=fitted_case[1]).snapshot_sha256
        == baseline.snapshot_sha256
    )


def test_capture_failure_rolls_back_package_and_run(fitted_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import snapshot

    pricing, _, candidate, _ = fitted_case

    def fail(bundle):
        raise RuntimeError("snapshot capture failed")

    monkeypatch.setattr(snapshot, "capture_monitoring_snapshot", fail)
    with pytest.raises(RuntimeError, match="snapshot capture failed"):
        api.save_model_version(pricing, candidate)
    with pricing.engine.connect() as connection:
        for table in (
            "MODEL_RECIPE",
            "MODEL_RUN",
            "PRICING_RATE_PACKAGE",
            "MODEL_MONITORING_BASELINE",
        ):
            assert (
                connection.execute(text(f"SELECT COUNT(*) FROM pricing.{table}")).scalar_one() == 0
            )


def test_unsupported_capture_preserves_publication_with_reason(fitted_case, monkeypatch):
    from pricing_pipeline.modeling.monitoring import snapshot
    from pricing_pipeline.modeling.monitoring.contracts import MonitoringError
    from pricing_pipeline.modeling.monitoring.storage import load_monitoring_baseline

    pricing, _, candidate, _ = fitted_case

    def unsupported(bundle):
        raise snapshot.MonitoringSnapshotUnsupported("custom feature cannot be stored")

    monkeypatch.setattr(snapshot, "capture_monitoring_snapshot", unsupported)
    saved = api.save_model_version(pricing, candidate)
    _deploy(pricing, saved)
    with pytest.raises(MonitoringError, match="custom feature cannot be stored"):
        load_monitoring_baseline(pricing.engine, saved.model_name)
    with pricing.engine.connect() as connection:
        row = (
            connection.execute(text("SELECT * FROM pricing.MODEL_MONITORING_BASELINE"))
            .mappings()
            .one()
        )
        assert row["capture_status"] == "UNAVAILABLE"
        assert row["snapshot_json"] is None


def test_legacy_publication_can_be_captured_once_without_refitting(fitted_case):
    from pricing_pipeline.modeling.monitoring import MonitoringError
    from pricing_pipeline.modeling.monitoring.storage import (
        capture_existing_monitoring_baseline,
        load_monitoring_baseline,
    )
    from pricing_pipeline.workbench.core import Workbench

    pricing, model, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    _deploy(pricing, saved)
    with pricing.engine.begin() as connection:
        connection.execute(text("DROP TRIGGER pricing.TR_MODEL_MONITORING_BASELINE_DELETE"))
        connection.execute(text("DELETE FROM pricing.MODEL_MONITORING_BASELINE"))
    with pytest.raises(MonitoringError, match="no SQL monitoring baseline"):
        load_monitoring_baseline(pricing.engine, saved.model_name)
    opened = Workbench(
        engine=pricing.engine, settings=pricing.settings, model_config=model.config
    ).open(saved.model_name, package_version=saved.package_version)
    digest = capture_existing_monitoring_baseline(opened)
    assert capture_existing_monitoring_baseline(opened) == digest
    assert load_monitoring_baseline(pricing.engine, saved.model_name).snapshot_sha256 == digest
    with pricing.engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RUN")).scalar_one() == 1


@pytest.mark.parametrize(
    "corruption, expected",
    [
        ("snapshot_json='{}'", "snapshot hash"),
        ("source_lineage_json='{}'", "source lineage hash"),
    ],
)
def test_loader_rejects_corrupted_snapshot_or_source_digest(fitted_case, corruption, expected):
    from pricing_pipeline.modeling.monitoring import MonitoringError
    from pricing_pipeline.modeling.monitoring.storage import load_monitoring_baseline

    pricing, _, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    _deploy(pricing, saved)
    with pricing.engine.begin() as connection:
        connection.execute(text("DROP TRIGGER pricing.TR_MODEL_MONITORING_BASELINE_UPDATE"))
        connection.execute(text(f"UPDATE pricing.MODEL_MONITORING_BASELINE SET {corruption}"))
    with pytest.raises(MonitoringError, match=expected):
        load_monitoring_baseline(pricing.engine, saved.model_name)


def test_loader_uses_current_deployment_in_requested_slot(fitted_case):
    from pricing_pipeline.modeling.monitoring import MonitoringError
    from pricing_pipeline.modeling.monitoring.storage import load_monitoring_baseline

    pricing, _, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    _deploy(pricing, saved)
    with pytest.raises(MonitoringError, match="one current deployed package"):
        load_monitoring_baseline(pricing.engine, saved.model_name, deployment_slot="UNDEPLOYED")
    with pricing.engine.begin() as connection:
        connection.execute(
            text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts='2999-01-01'")
        )
    with pytest.raises(MonitoringError, match="one current deployed package"):
        load_monitoring_baseline(pricing.engine, saved.model_name)


@pytest.mark.parametrize(
    "field, expected",
    [
        ("receipt", "receipt does not match"),
        ("bundle_identity", "bundle identity does not match"),
    ],
)
def test_capture_rejects_valid_snapshot_for_different_publication(
    fitted_case, monkeypatch, field, expected
):
    from pricing_pipeline.modeling.monitoring import MonitoringError, snapshot

    pricing, _, candidate, _ = fitted_case
    capture = snapshot.capture_monitoring_snapshot

    def mismatched(bundle):
        result = capture(bundle)
        document = json.loads(result.snapshot_json)
        if field == "receipt":
            document["receipt"]["package_metadata"]["mismatched"] = True
        else:
            document["bundle_identity"]["export_id"] = "other-export"
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return replace(
            result,
            snapshot_json=encoded,
            snapshot_sha256=hashlib.sha256(encoded.encode()).hexdigest(),
        )

    monkeypatch.setattr(snapshot, "capture_monitoring_snapshot", mismatched)
    with pytest.raises(MonitoringError, match=expected):
        api.save_model_version(pricing, candidate)
    with pricing.engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RUN")).scalar_one() == 0


@pytest.mark.parametrize(
    "variant", ["STATIC_SCORE", "FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"]
)
def test_sql_monitoring_persists_without_artifacts_and_rechecks_snapshot(fitted_case, variant):
    from pricing_pipeline.modeling.monitoring import (
        MonitoringError,
        check_monitoring_data,
        persist_monitoring_fit,
        run_monitoring_fit,
    )

    pricing, model, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    _deploy(pricing, saved)
    for filename in (
        candidate.completed_build.candidate_artifact_path,
        candidate.completed_build.rating_workbook_path,
        candidate.completed_build.publication_receipt_path,
    ):
        Path(filename).unlink()
    baseline = api.load_monitoring_baseline(pricing, model=model)
    frame = api.apply_transforms(model.spec.dataset.df, model.spec.transforms)
    frame["as_of"] = "2026-09-02"
    frame["claim_count"] = frame.claim_count + 1
    X = frame.loc[:, list(model.spec.features)]
    check = check_monitoring_data(baseline, X, variant=variant)
    assert check.compatible
    assert not check.distributions.empty
    result = run_monitoring_fit(
        baseline,
        X,
        frame.claim_count,
        offset=frame.log_exposure,
        variant=variant,
        model_frame=frame,
        target_column="claim_count",
        offset_column="log_exposure",
        max_reml_iter=3,
        runtime_validation="skip",
    )
    with pricing.engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO pricing.DATASET_MANIFEST
                (manifest_id, dataset_name, data_as_of_date, row_count, pk_columns_json,
                 target_column, offset_column, offset_source_column, offset_label, export_weight_column,
                 model_frame_sha256, frame_hash_metadata_json, created_by)
                VALUES ('monitor-data','claims','2026-09-02',:rows,'["id"]',
                    'claim_count','log_exposure',:offset_source,:label,'exposure',:sha,'{}','test')"""),
            {
                "rows": len(frame),
                "label": baseline.offset_contract.label,
                "offset_source": baseline.offset_contract.source_name,
                "sha": result.model_frame_sha256,
            },
        )
    arguments = {
        "baseline_model_run_id": saved.model_run_id,
        "baseline_deployment_id": baseline.identity["deployment_id"],
        "manifest_id": "monitor-data",
        "created_by": "test",
    }
    recorded = persist_monitoring_fit(pricing.engine, result, **arguments)
    assert (
        persist_monitoring_fit(pricing.engine, result, **arguments).monitor_run_id
        == recorded.monitor_run_id
    )
    with pricing.engine.begin() as connection:
        assert (
            connection.execute(text("SELECT COUNT(*) FROM pricing.MODEL_MONITOR_RUN")).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.PRICING_RATE_PACKAGE")
            ).scalar_one()
            == 1
        )
        connection.execute(text("DROP TRIGGER pricing.TR_MODEL_MONITORING_BASELINE_UPDATE"))
        connection.execute(text("UPDATE pricing.MODEL_MONITORING_BASELINE SET snapshot_json='{}'"))
    with pytest.raises(MonitoringError, match="snapshot hash"):
        persist_monitoring_fit(pricing.engine, result, **arguments)
    with pricing.engine.begin() as connection:
        connection.execute(
            text("UPDATE pricing.MODEL_MONITORING_BASELINE SET snapshot_json=:snapshot"),
            {"snapshot": baseline.snapshot_json},
        )
        connection.execute(
            text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts='2999-01-01'")
        )
    with pytest.raises(MonitoringError, match="baseline_deployment_id"):
        persist_monitoring_fit(pricing.engine, result, **arguments)
