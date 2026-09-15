"""Monitoring refits keep their own publication identity and immutable SQL link."""

import json
import re
import sqlite3
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from pricing_pipeline import notebook as api
from pricing_pipeline.modeling.monitoring import persist_monitoring_fit, run_monitoring_fit
from pricing_pipeline.models.spec import ApprovedModelBuild, ApprovedModelBuildError


def _publish_challenger(case, *, receipt=None, result=None):
    from pricing_pipeline.data.manifest import DatasetManifestResult, ModelFrameManifestSpec
    from pricing_pipeline.modeling.monitoring.challengers import (
        MonitoringPublicationConfig,
        publish_monitoring_challenger,
    )

    pricing, model, champion, _, recorded, fitted = case
    baseline = api.load_monitoring_baseline(pricing, model=model)
    frame = api.apply_transforms(model.spec.dataset.df, model.spec.transforms)
    with pricing.engine.connect() as connection:
        row = (
            connection.execute(
                text("SELECT * FROM pricing.DATASET_MANIFEST WHERE manifest_id=:manifest"),
                {"manifest": champion.completed_build.manifest_id},
            )
            .mappings()
            .one()
        )
    spec = ModelFrameManifestSpec(
        dataset_name=row["dataset_name"],
        source_system=row["source_system"],
        data_as_of_date=row["data_as_of_date"],
        data_as_of_column=row["data_as_of_column"],
        pk_columns=tuple(json.loads(row["pk_columns_json"])),
        feature_columns=baseline.feature_names,
        **{
            name: row[name]
            for name in (
                "target_column",
                "weight_column",
                "offset_column",
                "offset_source_column",
                "offset_label",
                "export_weight_column",
            )
        },
    )
    return publish_monitoring_challenger(
        pricing.engine,
        baseline=baseline,
        result=fitted if result is None else result,
        receipt=recorded if receipt is None else receipt,
        df=frame,
        manifest=DatasetManifestResult(row["manifest_id"], row["model_frame_sha256"]),
        manifest_spec=spec,
        publication=MonitoringPublicationConfig(pricing.settings, model.config, model.model_id),
        created_by="test",
    )


@pytest.fixture
def monitoring_publication_case(fitted_case):
    pricing, model, champion, glm = fitted_case
    saved = api.save_model_version(pricing, champion)
    with pricing.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE pricing.PRICING_RATE_PACKAGE SET package_status='PUBLISHED' WHERE rate_package_id=:package"
            ),
            {"package": saved.rate_package_id},
        )
        connection.execute(
            text(
                "INSERT INTO pricing.PRICING_MODEL_DEPLOYMENT (model_id,rate_package_id,deployment_slot,effective_from_ts,deployed_by) VALUES (:model,:package,'PRODUCTION',CURRENT_TIMESTAMP,'test')"
            ),
            {"model": saved.model_id, "package": saved.rate_package_id},
        )
    baseline = api.load_monitoring_baseline(pricing, model=model)
    frame = api.apply_transforms(model.spec.dataset.df, model.spec.transforms)
    result = run_monitoring_fit(
        baseline,
        frame.loc[:, list(model.spec.features)],
        frame.claim_count,
        offset=frame.log_exposure,
        variant="FROZEN_REFIT",
        model_frame=frame,
        target_column="claim_count",
        offset_column="log_exposure",
        continuous_points=11,
        max_reml_iter=3,
        runtime_validation="skip",
    )
    recorded = persist_monitoring_fit(
        pricing.engine,
        result,
        baseline_model_run_id=saved.model_run_id,
        baseline_deployment_id=baseline.deployment_id,
        manifest_id=champion.completed_build.manifest_id,
        created_by="test",
    )
    return pricing, model, champion, glm, recorded, result


def test_build_accepts_monitor_run_identity(fitted_case):
    build = fitted_case[2].completed_build
    monitor_run_id = str(uuid4())
    restored = ApprovedModelBuild(**{**build.model_dump(), "monitor_run_id": monitor_run_id})
    assert restored.monitor_run_id == monitor_run_id


@pytest.mark.parametrize("value", ["", "not-a-run", 42])
def test_build_rejects_invalid_monitor_run_identity(fitted_case, value):
    build = fitted_case[2].completed_build
    with pytest.raises(ApprovedModelBuildError, match="monitor_run_id"):
        ApprovedModelBuild(**{**build.model_dump(), "monitor_run_id": value})


def test_monitoring_publication_validation_reads_sealed_refit(monitoring_publication_case):
    from pricing_pipeline.publishing.monitoring import validate_monitoring_publication

    pricing, _, champion, _, recorded, _ = monitoring_publication_case
    build = SimpleNamespace(
        monitor_run_id=recorded.monitor_run_id,
        model_id=champion.completed_build.model_id,
        manifest_id=champion.completed_build.manifest_id,
        model_frame_sha256=champion.completed_build.model_frame_sha256,
    )
    with pricing.engine.begin() as connection:
        row = validate_monitoring_publication(connection, build)
        assert row["variant_code"] == "FROZEN_REFIT"
        assert row["baseline_model_run_id"] is not None
        for field, value in (("model_id", -1), ("manifest_id", "wrong")):
            broken = SimpleNamespace(**{**vars(build), field: value})
            with pytest.raises(ValueError, match=field):
                validate_monitoring_publication(connection, broken)


def test_monitoring_publication_requires_captured_state_and_is_immutable(
    monitoring_publication_case,
):
    from pricing_pipeline.publishing.monitoring import save_monitoring_publication

    pricing, _, champion, _, recorded, _ = monitoring_publication_case
    build = champion.completed_build.model_copy(update={"monitor_run_id": recorded.monitor_run_id})
    with (
        pytest.raises(ValueError, match="monitoring fit|evidence"),
        pricing.engine.begin() as connection,
    ):
        # The champion's saved model is not the refitted monitoring result.
        save_monitoring_publication(connection, build=build, model_run_id=1)
    with pricing.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.MODEL_MONITOR_PUBLICATION")
            ).scalar_one()
            == 0
        )


def test_monitoring_link_rejects_unsealed_or_static_observation(monitoring_publication_case):
    from pricing_pipeline.publishing.monitoring import validate_monitoring_publication

    pricing, _, champion, _, recorded, _ = monitoring_publication_case
    build = champion.completed_build.model_copy(update={"monitor_run_id": recorded.monitor_run_id})
    with pricing.engine.begin() as connection:
        connection.execute(text("DROP TRIGGER pricing.TR_MODEL_MONITOR_RUN_IMMUTABLE_UPDATE"))
        for field, value in (("evidence_sealed", 0), ("variant_code", "STATIC_SCORE")):
            connection.execute(
                text(
                    f"UPDATE pricing.MODEL_MONITOR_RUN SET {field}=:value WHERE monitor_run_id=:run"
                ),
                {"value": value, "run": recorded.monitor_run_id},
            )
            with pytest.raises(ValueError, match="sealed|refit"):
                validate_monitoring_publication(connection, build)
            connection.execute(
                text(
                    "UPDATE pricing.MODEL_MONITOR_RUN SET evidence_sealed=1,variant_code='FROZEN_REFIT' WHERE monitor_run_id=:run"
                ),
                {"run": recorded.monitor_run_id},
            )


def test_exact_refit_publication_is_immutable_and_reuses_sql_only(
    monitoring_publication_case, monkeypatch
):
    from pricing_pipeline.modeling.monitoring import challengers
    from pricing_pipeline.publishing.identity import find_equivalent_publication
    from pricing_pipeline.publishing.monitoring import (
        find_monitoring_publication,
        validate_export_monitoring_link,
    )
    from pricing_pipeline.publishing.publish import PublicationRequest, prepare_publication
    from pricing_pipeline.publishing.sqlite import _equivalent_local_publication

    pricing, model, _, _, recorded, _ = monitoring_publication_case
    exported = []
    original_export = challengers.export_fitted_superglm_build

    def capture_build(**kwargs):
        build = original_export(**kwargs)
        exported.append(build)
        return build

    monkeypatch.setattr(challengers, "export_fitted_superglm_build", capture_build)
    published = _publish_challenger(monitoring_publication_case)
    assert not published["was_existing"]
    found = find_monitoring_publication(pricing.engine, recorded.monitor_run_id)
    assert found["rate_package_id"] == published["rate_package_id"]
    assert str(found["baseline_model_run_id"]) != str(found["model_run_id"])
    monkeypatch.setattr(
        challengers,
        "export_fitted_superglm_build",
        lambda **kwargs: pytest.fail("retry exported files"),
    )
    repeated = _publish_challenger(monitoring_publication_case)
    assert repeated["publication_reused"]
    assert repeated["rate_package_id"] == published["rate_package_id"]
    ordinary = exported[0].model_copy(update={"monitor_run_id": None})
    ordinary = ordinary.model_copy(
        update={"model_equivalence_sha256": published["model_equivalence_sha256"]}
    )
    assert find_equivalent_publication(pricing.engine, build=ordinary) is None
    with pricing.engine.connect() as connection:
        prepared = prepare_publication(
            PublicationRequest(
                build=ordinary,
                model_config=model.config,
                execution_name="test",
                execution_id="test",
                allowed_artifact_root=pricing.settings.workbench_artifact_root,
            )
        )
        assert _equivalent_local_publication(connection, prepared) is None
        with pytest.raises(ValueError, match="monitor_run_id"):
            validate_export_monitoring_link(connection, ordinary, published["model_run_id"])
        view = connection.execute(text("SELECT * FROM pricing.V_MODEL_CHALLENGER")).mappings().one()
        assert view["monitor_run_id"] == recorded.monitor_run_id
        assert view["variant_code"] == "FROZEN_REFIT"
        assert view["is_current_champion"] == 0
        assert view["current_rate_package_id"] != published["rate_package_id"]
        assert view["data_as_of_date"] == view["baseline_data_as_of_date"]
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.PRICING_RATE_PACKAGE")
            ).scalar_one()
            == 2
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.PRICING_MODEL_DEPLOYMENT")
            ).scalar_one()
            == 1
        )
    for statement in (
        "UPDATE pricing.MODEL_MONITOR_PUBLICATION SET created_by='changed'",
        "DELETE FROM pricing.MODEL_MONITOR_PUBLICATION",
    ):
        with pytest.raises(IntegrityError, match="immutable"), pricing.engine.begin() as connection:
            connection.execute(text(statement))
    from pricing_pipeline.workbench.champion import list_challengers, review_model_version

    with pricing.engine.begin() as connection:
        # Exercise the SQL Server review contract with a published offline package.
        connection.execute(
            text(
                "UPDATE pricing.PRICING_RATE_PACKAGE SET package_status='PUBLISHED' WHERE rate_package_id=:package"
            ),
            {"package": published["rate_package_id"]},
        )
    review = review_model_version(
        pricing.engine,
        model_config=model.config,
        model_id=model.model_id,
        package_version=published["package_version"],
    )
    assert review.monitor_run_id == recorded.monitor_run_id
    assert review.monitoring_variant == "FROZEN_REFIT"
    assert review.data_as_of_date == review.baseline_data_as_of_date
    choices = list_challengers(pricing.engine, model_config=model.config, model_id=model.model_id)
    assert len(choices) == 2
    assert choices.is_current_champion.sum() == 1


def test_changed_exported_coefficients_roll_back_challenger_package(
    monitoring_publication_case, monkeypatch
):
    from pricing_pipeline.modeling.monitoring import challengers

    pricing = monitoring_publication_case[0]
    export = challengers.export_fitted_superglm_build

    def alter_after_fit_verification(**kwargs):
        fitted = kwargs["fitted_model"]
        fitted._result = replace(fitted.result, beta=fitted.result.beta + 0.5)
        return export(**kwargs)

    monkeypatch.setattr(challengers, "export_fitted_superglm_build", alter_after_fit_verification)
    with pytest.raises(ValueError, match="coefficients.*monitoring fit evidence"):
        _publish_challenger(monitoring_publication_case)
    with pricing.engine.connect() as connection:
        for table in ("MODEL_RUN", "PRICING_RATE_PACKAGE", "MODEL_MONITORING_BASELINE"):
            assert (
                connection.execute(text(f"SELECT COUNT(*) FROM pricing.{table}")).scalar_one() == 1
            )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.MODEL_MONITOR_PUBLICATION")
            ).scalar_one()
            == 0
        )


def test_challenger_link_preserves_baseline_training_manifest(fitted_case):
    from pricing_pipeline.modeling.monitoring.batch import run_monitoring_batch
    from pricing_pipeline.modeling.monitoring.challengers import MonitoringPublicationConfig
    from tests.recipes.test_monitoring_batch import _fresh_dataset, _published_baseline

    pricing, model, candidate, _ = fitted_case
    baseline, _ = _published_baseline(pricing, model, candidate)
    report = run_monitoring_batch(
        pricing.engine,
        baseline,
        _fresh_dataset(),
        target_column="claim_count",
        created_by="test",
        continuous_points=9,
        max_reml_iter=3,
        publication=MonitoringPublicationConfig(pricing.settings, model.config, model.model_id),
    )
    assert report.manifest_id != candidate.completed_build.manifest_id
    with pytest.raises(IntegrityError, match="immutable"), pricing.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE pricing.DATASET_MANIFEST SET data_as_of_date='2099-01-01' WHERE manifest_id=:manifest"
            ),
            {"manifest": candidate.completed_build.manifest_id},
        )


@pytest.mark.parametrize(
    "variant,sealed,capture,model,manifest,candidate_run,rejected",
    [
        ("FROZEN_REFIT", 1, "CAPTURED", 1, "current", 11, False),
        ("STATIC_SCORE", 1, "CAPTURED", 1, "current", 11, True),
        ("FROZEN_REFIT", 0, "CAPTURED", 1, "current", 11, True),
        ("FROZEN_REFIT", 1, "UNAVAILABLE", 1, "current", 11, True),
        ("FROZEN_REFIT", 1, "CAPTURED", None, "current", 11, True),
        ("FROZEN_REFIT", 1, "CAPTURED", 1, "wrong", 11, True),
        ("FROZEN_REFIT", 1, "CAPTURED", 1, "current", 10, True),
    ],
)
def test_sqlserver_challenger_guard_rejects_invalid_lineage(
    variant, sealed, capture, model, manifest, candidate_run, rejected
):
    """Run the migration predicate with SQL NULL semantics, without installing T-SQL."""
    from pricing_pipeline.resources import migration_root

    migration = (
        migration_root().joinpath("V050__monitoring_challenger_publications.sql").read_text()
    )
    predicate = re.search(r"IF EXISTS \((.*?)\) THROW", migration, re.DOTALL)[1]
    with sqlite3.connect(":memory:") as connection:
        connection.executescript("""
            ATTACH ':memory:' AS pricing;
            ATTACH ':memory:' AS mlops;
            CREATE TABLE inserted (monitor_run_id TEXT, model_run_id INTEGER);
            CREATE TABLE mlops.MODEL_MONITOR_RUN (monitor_run_id TEXT,fit_contract_id TEXT,
                evidence_sealed INTEGER,run_status TEXT,invariant_status TEXT,variant_code TEXT,model_id INTEGER,manifest_id TEXT);
            CREATE TABLE mlops.MODEL_FIT_CONTRACT (fit_contract_id TEXT,baseline_model_run_id INTEGER);
            CREATE TABLE pricing.MODEL_RUN (model_run_id INTEGER,model_id INTEGER,manifest_id TEXT,rate_package_id INTEGER,run_status TEXT);
            CREATE TABLE pricing.PRICING_RATE_PACKAGE (rate_package_id INTEGER,package_status TEXT);
            CREATE TABLE pricing.MODEL_MONITORING_BASELINE (model_run_id INTEGER,capture_status TEXT);
            INSERT INTO mlops.MODEL_FIT_CONTRACT VALUES ('contract',10);
            INSERT INTO pricing.PRICING_RATE_PACKAGE VALUES (12,'PUBLISHED');
        """)
        connection.execute("INSERT INTO inserted VALUES ('monitor',?)", (candidate_run,))
        connection.execute(
            "INSERT INTO mlops.MODEL_MONITOR_RUN VALUES ('monitor','contract',?,'SUCCESS','VERIFIED',?,1,'current')",
            (sealed, variant),
        )
        connection.execute(
            "INSERT INTO pricing.MODEL_RUN VALUES (?,?,?,12,'SUCCESS')",
            (candidate_run, model, manifest),
        )
        connection.execute(
            "INSERT INTO pricing.MODEL_MONITORING_BASELINE VALUES (?,?)", (candidate_run, capture)
        )
        assert bool(connection.execute(predicate).fetchall()) is rejected
