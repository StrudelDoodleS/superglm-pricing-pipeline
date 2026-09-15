"""SQL review records preserve the exact champion seen before explicit promotion."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest
from sqlalchemy import event, text

from pricing_pipeline.infra.offline_sqlite import (
    apply_offline_ddl,
    sqlite_engine_with_offline_schemas,
)
from pricing_pipeline.models.config import ModelBuildConfig


@pytest.fixture
def sql_review_case(tmp_path):
    engine = sqlite_engine_with_offline_schemas(
        {schema: tmp_path / f"{schema}.sqlite" for schema in ("pricing", "pricing_stg", "mlops")}
    )
    apply_offline_ddl(engine)
    config = ModelBuildConfig(
        model_name="TEST_FREQ",
        model_label="Test frequency",
        target_name="claims",
        model_type="frequency",
        deployment_slot="TEST_CURRENT",
    )
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO pricing.PRICING_MODEL
            (model_id,model_name,target_name,model_type,created_by)
            VALUES (17,'TEST_FREQ','claims','frequency','test')""")
        )
        for version, as_at in ((1, "2026-08-31"), (2, "2026-09-15")):
            connection.execute(
                text("""INSERT INTO pricing.DATASET_MANIFEST
                (manifest_id,dataset_name,data_as_of_date,row_count,pk_columns_json,
                 model_frame_sha256,frame_hash_metadata_json,created_by)
                VALUES (:manifest,'claims',:as_at,10,'["id"]',:sha,'{}','test')"""),
                {"manifest": f"manifest-{version}", "as_at": as_at, "sha": str(version) * 64},
            )
            connection.execute(
                text("""INSERT INTO pricing.PRICING_RATE_PACKAGE
                (rate_package_id,model_id,model_name,model_version,package_version,
                 base_rate,package_status,created_by)
                VALUES (:package,17,'TEST_FREQ',:version,:version,1.0,'PUBLISHED','test')"""),
                {"package": 100 + version, "version": version},
            )
            files = [tmp_path / f"v{version}.{suffix}" for suffix in ("joblib", "xlsx", "json")]
            for path in files:
                path.write_text("removed publication file")
                path.unlink()
            connection.execute(
                text("""INSERT INTO pricing.MODEL_RUN
                (model_run_id,model_id,model_name,model_version,model_kind,export_id,
                 manifest_id,rate_package_id,rating_workbook_path,rating_workbook_sha256,
                 candidate_artifact_path,publication_receipt_path,run_status,created_by)
                VALUES (:run,17,'TEST_FREQ',:version,'RAW',:export,:manifest,:package,
                        :workbook,:sha,:artifact,:receipt,'SUCCESS','test')"""),
                {
                    "run": str(version),
                    "version": version,
                    "export": f"export-{version}",
                    "manifest": f"manifest-{version}",
                    "package": 100 + version,
                    "artifact": str(files[0]),
                    "workbook": str(files[1]),
                    "receipt": str(files[2]),
                    "sha": "a" * 64,
                },
            )
            connection.execute(
                text("""INSERT INTO mlops.MODEL_RUN_METRIC
                (model_run_id,metric_name,metric_value,metric_scope)
                VALUES (:run,'fit_deviance',:deviance,'full_fit')"""),
                {"run": str(version), "deviance": 10.0 - version},
            )
    yield engine, config
    engine.dispose()


def _review(engine, config, version=2):
    from pricing_pipeline.workbench.champion import review_model_version

    return review_model_version(engine, model_config=config, model_id=17, package_version=version)


def _deploy_fixture(engine, package=101, slot="TEST_CURRENT"):
    with engine.begin() as connection:
        return connection.execute(
            text("""INSERT INTO pricing.PRICING_MODEL_DEPLOYMENT
            (model_id,rate_package_id,deployment_slot,effective_from_ts,deployed_by)
            VALUES (17,:package,:slot,CURRENT_TIMESTAMP,'test')"""),
            {"package": package, "slot": slot},
        ).lastrowid


def test_review_is_sql_only_with_no_files_or_fitting_and_does_not_deploy(
    sql_review_case, monkeypatch
):
    from superglm import SuperGLM

    from pricing_pipeline.workbench import artifacts

    engine, config = sql_review_case
    monkeypatch.setattr(
        artifacts, "load_candidate_bundle", lambda *a, **k: pytest.fail("artifact read")
    )
    monkeypatch.setattr(SuperGLM, "fit", lambda *a, **k: pytest.fail("fit"))
    monkeypatch.setattr(SuperGLM, "fit_reml", lambda *a, **k: pytest.fail("fit_reml"))
    statements = []
    event.listen(engine, "before_cursor_execute", lambda c, u, s, p, x, m: statements.append(s))

    reviewed = _review(engine, config)

    assert reviewed.engine is engine
    assert reviewed.model_config == config
    assert reviewed.rate_package_id == 102
    assert reviewed.package_version == 2
    assert str(reviewed.model_run_id) == "2"
    assert reviewed.manifest_id == "manifest-2"
    assert str(reviewed.data_as_of_date) == "2026-09-15"
    assert reviewed.model_kind == "RAW"
    assert reviewed.monitoring_variant is None
    assert reviewed.current_rate_package_id is None
    assert reviewed.current_deployment_id is None
    assert not reviewed.summary.empty
    assert reviewed.metrics.metric_value.tolist() == [8.0]
    assert not any(
        statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for statement in statements
    )
    with pytest.raises(FrozenInstanceError):
        reviewed.rate_package_id = 101
    edited = reviewed.summary
    edited.loc[:, "rate_package_id"] = 999
    assert reviewed.summary.iloc[0].rate_package_id == 102
    edited_metrics = reviewed.metrics
    edited_metrics.loc[:, "metric_value"] = 999
    assert reviewed.metrics.metric_value.tolist() == [8.0]
    with engine.connect() as connection:
        paths = connection.execute(
            text("SELECT candidate_artifact_path FROM pricing.MODEL_RUN")
        ).scalars()
        assert all(not Path(path).exists() for path in paths)
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.PRICING_MODEL_DEPLOYMENT")
            ).scalar_one()
            == 0
        )


def test_review_captures_champion_identity_and_date_for_configured_slot(sql_review_case):
    engine, config = sql_review_case
    expected = _deploy_fixture(engine)
    _deploy_fixture(engine, 102, "OTHER_SLOT")
    reviewed = _review(engine, config)
    assert reviewed.current_deployment_id == expected
    assert reviewed.current_rate_package_id == 101
    assert reviewed.current_manifest_id == "manifest-1"
    assert str(reviewed.current_data_as_of_date) == "2026-08-31"
    assert set(reviewed.metrics.role) == {"selected", "current_champion"}
    assert set(reviewed.metrics.metric_scope) == {"full_fit"}


def test_listing_returns_sql_challengers_and_marks_current_champion(sql_review_case):
    from pricing_pipeline.workbench.champion import list_challengers

    engine, config = sql_review_case
    _deploy_fixture(engine)
    rows = list_challengers(engine, model_config=config, model_id=17)
    assert rows.package_version.tolist() == [2, 1]
    assert rows.is_current_champion.tolist() == [False, True]
    assert rows.manifest_id.tolist() == ["manifest-2", "manifest-1"]


@pytest.mark.parametrize(
    "changes", [{"model_name": "OTHER"}, {"target_name": "other"}, {"model_type": "other"}]
)
def test_review_requires_matching_registered_model_config(sql_review_case, changes):
    from pricing_pipeline.workbench.champion import ModelVersionReviewError

    engine, config = sql_review_case
    with pytest.raises(ModelVersionReviewError, match="model|config"):
        _review(engine, replace(config, **changes))


@pytest.mark.parametrize(
    "field,value", [("package_status", "LOCAL_AUDIT"), ("package_status", "DRAFT")]
)
def test_review_requires_published_selected_package(sql_review_case, field, value):
    from pricing_pipeline.workbench.champion import ModelVersionReviewError

    engine, config = sql_review_case
    with engine.begin() as connection:
        connection.execute(
            text(
                f"UPDATE pricing.PRICING_RATE_PACKAGE SET {field}=:value WHERE rate_package_id=102"
            ),
            {"value": value},
        )
    with pytest.raises(ModelVersionReviewError, match="published"):
        _review(engine, config)


@pytest.mark.parametrize("deployed", [False, True])
def test_promotion_passes_both_reviewed_ids_without_refreshing_them(
    sql_review_case, monkeypatch, deployed
):
    from pricing_pipeline.workbench import champion

    engine, config = sql_review_case
    expected_id = _deploy_fixture(engine) if deployed else None
    reviewed = _review(engine, config)
    if deployed:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts='2099-01-01'")
            )
    _deploy_fixture(engine, package=102)
    calls = []
    monkeypatch.setattr(
        champion, "deploy_rate_package", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    champion.promote_model_version(reviewed, deployment_reason="approved", deployed_by="reviewer")
    assert calls[0][0] == (engine, config)
    assert calls[0][1]["rate_package_id"] == 102
    assert calls[0][1]["expected_current_rate_package_id"] == (101 if deployed else None)
    assert calls[0][1]["expected_current_deployment_id"] == expected_id


def test_promotion_rechecks_selected_package_before_deployment(sql_review_case, monkeypatch):
    from pricing_pipeline.workbench import champion

    engine, config = sql_review_case
    reviewed = _review(engine, config)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE pricing.PRICING_RATE_PACKAGE SET package_status='DRAFT' WHERE rate_package_id=102"
            )
        )
    monkeypatch.setattr(
        champion, "deploy_rate_package", lambda *a, **k: pytest.fail("deployment reached")
    )
    with pytest.raises(champion.ModelVersionReviewError, match="published"):
        champion.promote_model_version(
            reviewed, deployment_reason="approved", deployed_by="reviewer"
        )


def _monitoring_publication(engine):
    deployment_id = _deploy_fixture(engine)
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO pricing.MODEL_FIT_CONTRACT
            (fit_contract_id,baseline_model_run_id,model_id,rate_package_id,contract_schema_version,
             contract_sha256,structure_sha256,contract_json,superglm_version,created_by)
            VALUES ('contract','1',17,101,1,:sha,:sha,'{}','test','test')"""),
            {"sha": "a" * 64},
        )
        connection.execute(
            text("""INSERT INTO pricing.MODEL_MONITORING_BASELINE
            (model_run_id,model_id,rate_package_id,capture_status,snapshot_schema_version,
             snapshot_json,snapshot_sha256,superglm_version,source_lineage_json,
             source_lineage_sha256,created_by)
            VALUES ('2',17,102,'CAPTURED',1,'{}',:sha,'test','{}',:sha,'test')"""),
            {"sha": "a" * 64},
        )
        observations = [
            ("refit", "FROZEN_REFIT", "manifest-2", "FREQUENCY", 8.0),
            ("same-data-baseline", "STATIC_SCORE", "manifest-2", "FREQUENCY", 12.0),
            ("old-data-baseline", "STATIC_SCORE", "manifest-1", "FREQUENCY", 777.0),
            ("other-component", "STATIC_SCORE", "manifest-2", "OTHER", 888.0),
        ]
        for number, (run, variant, manifest, component, value) in enumerate(observations, 1):
            connection.execute(
                text("""INSERT INTO pricing.MODEL_MONITOR_RUN
                (monitor_run_id,fit_contract_id,baseline_deployment_id,model_id,rate_package_id,
                 manifest_id,component_role,variant_code,run_signature_sha256,run_status,
                 invariant_status,invariant_evidence_sha256,invariant_evidence_json,
                 model_frame_sha256,fit_configuration_json,result_evidence_sha256,created_by,evidence_sealed)
                VALUES (:run,'contract',:deployment,17,101,:manifest,:component,:variant,
                        :sha,'SUCCESS','VERIFIED',:sha,'{}',:sha,'{}',:sha,'test',0)"""),
                {
                    "run": run,
                    "deployment": deployment_id,
                    "manifest": manifest,
                    "component": component,
                    "variant": variant,
                    "sha": str(number) * 64,
                },
            )
            connection.execute(
                text("""INSERT INTO pricing.MODEL_MONITOR_METRIC
                (monitor_run_id,metric_name,metric_value) VALUES (:run,'deviance',:value)"""),
                {"run": run, "value": value},
            )
            connection.execute(
                text(
                    "UPDATE pricing.MODEL_MONITOR_RUN SET evidence_sealed=1 WHERE monitor_run_id=:run"
                ),
                {"run": run},
            )
        connection.execute(
            text("""INSERT INTO pricing.MODEL_MONITOR_PUBLICATION
            (monitor_run_id,model_run_id,created_by) VALUES ('refit','2','test')""")
        )
    return deployment_id


def test_monitoring_review_compares_static_and_refit_on_the_same_dataset(sql_review_case):
    engine, config = sql_review_case
    _monitoring_publication(engine)
    reviewed = _review(engine, config)
    assert reviewed.monitoring_variant == "FROZEN_REFIT"
    assert reviewed.monitor_run_id == "refit"
    assert reviewed.baseline_data_as_of_date == "2026-08-31"
    metrics = reviewed.metrics
    assert set(metrics.monitor_run_id) == {"refit", "same-data-baseline"}
    assert set(metrics.manifest_id) == {"manifest-2"}
    assert set(metrics.data_as_of_date) == {"2026-09-15"}
    assert metrics.set_index("role").metric_value.to_dict() == {
        "selected": 8.0,
        "baseline_at_fit": 12.0,
    }
    assert set(metrics.metric_scope) == {"monitoring_snapshot"}


def test_monitoring_baseline_metrics_do_not_claim_to_score_a_new_champion(sql_review_case):
    engine, config = sql_review_case
    _monitoring_publication(engine)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts='2099-01-01'")
        )
    _deploy_fixture(engine, package=102)
    reviewed = _review(engine, config)
    assert reviewed.current_rate_package_id == 102
    assert "current_champion" not in set(reviewed.metrics.role)
    assert str(reviewed.metrics.set_index("role").loc["baseline_at_fit", "model_run_id"]) == "1"


def test_monitoring_challenger_is_bound_to_its_origin_deployment_slot(sql_review_case):
    from pricing_pipeline.workbench.champion import ModelVersionReviewError

    engine, config = sql_review_case
    _monitoring_publication(engine)
    with pytest.raises(ModelVersionReviewError, match="slot"):
        _review(engine, replace(config, deployment_slot="OTHER_SLOT"))
