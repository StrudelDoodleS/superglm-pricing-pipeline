from __future__ import annotations

from sqlalchemy import text

from pricing_pipeline.infra.migrations import migration_files
from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.resources import migration_root, offline_sqlite_root

OFFLINE_NAMES = ("mlops.sql", "pricing.sql", "pricing_stg.sql", "pricing_views.sql")

EXPECTED_MIGRATIONS = (
    "V001__dataset_manifest_cv.sql",
    "V002__pricing_core_minimal.sql",
    "V003__superglm_staging.sql",
    "V004__compiled_rating_tables.sql",
    "V005__fremtpl_raw_model_run.sql",
    "V006__model_registry_deployments.sql",
    "V007__cv_split_sets.sql",
    "V008__compiled_band_sort_order.sql",
    "V009__current_dataset_cv_fold_view.sql",
    "V010__cv_split_runtime_metadata.sql",
    "V011__cv_split_runtime_metadata_view.sql",
    "V012__clean_pricing_schema_tables.sql",
    "V013__model_run_lineage_tables.sql",
    "V014__current_rate_prediction_proc.sql",
    "V015__rate_package_immutability.sql",
    "V016__rate_package_version_and_deploy_guards.sql",
    "V017__rate_package_source_export_id.sql",
    "V018__drop_cv_split_row_if_empty.sql",
    "V019__terminate_throw_guard_errors.sql",
    "V020__rate_package_source_file.sql",
    "V021__unify_model_name.sql",
    "V022__superglm_publication_receipt_metadata.sql",
    "V023__model_relativity_bi_views.sql",
    "V024__candidate_model_artifacts.sql",
    "V025__package_specific_scoring.sql",
    "V026__nullable_candidate_effective_date.sql",
    "V027__model_version_reservations.sql",
    "V028__staging_content_digest.sql",
    "V029__current_rate_package_scoring.sql",
    "V030__staging_content_digest_binary_collation.sql",
    "V031__model_run_parent_lineage.sql",
    "V032__model_run_rating_workbook_digest.sql",
    "V033__dataset_manifest_frame_evidence.sql",
    "V034__dataset_manifest_offset_contract.sql",
    "V035__validation_metrics_and_final_relativity_views.sql",
    "V036__model_kind_manifest_relativity.sql",
    "V037__controlled_model_monitoring.sql",
    "V038__manual_edit_model_kind.sql",
)


def test_offline_sqlite_resource_inventory_is_exact():
    root = offline_sqlite_root()
    assert tuple(sorted(item.name for item in root.iterdir() if item.is_file())) == OFFLINE_NAMES
    assert all(root.joinpath(name).read_text(encoding="utf-8").strip() for name in OFFLINE_NAMES)


def test_sql_server_migration_inventory_is_exact_and_ordered(monkeypatch, tmp_path):
    monkeypatch.setenv("PRICING_SCHEMA_DIR", str(tmp_path / "poison"))
    resources = migration_files()
    assert tuple(item.name for item in resources) == EXPECTED_MIGRATIONS
    assert all(item.read_text(encoding="utf-8").strip() for item in resources)
    assert tuple(item.name for item in migration_root().iterdir() if item.is_file()) != ()


def test_offline_bootstrap_works_outside_checkout(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setenv("PRICING_SCHEMA_DIR", str(tmp_path / "poison"))

    engine, _paths = open_offline_sqlite(tmp_path / "database")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RUN")).scalar_one() == 0
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.MODEL_MONITOR_VARIANT")
            ).scalar_one()
            == 4
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM pricing.V_CURRENT_DEPLOYED_RELATIVITY")
            ).scalar_one()
            == 0
        )
