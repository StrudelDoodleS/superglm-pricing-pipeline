from __future__ import annotations

from sqlalchemy import text

from pricing_pipeline.infra.offline_sqlite import open_offline_sqlite
from pricing_pipeline.resources import offline_sqlite_root

OFFLINE_NAMES = ("mlops.sql", "pricing.sql", "pricing_stg.sql", "pricing_views.sql")


def test_offline_sqlite_resource_inventory_is_exact():
    root = offline_sqlite_root()
    assert tuple(sorted(item.name for item in root.iterdir() if item.is_file())) == OFFLINE_NAMES
    assert all(root.joinpath(name).read_text(encoding="utf-8").strip() for name in OFFLINE_NAMES)


def test_offline_bootstrap_works_outside_checkout(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setenv("PRICING_SCHEMA_DIR", str(tmp_path / "poison"))

    engine, _paths = open_offline_sqlite(tmp_path / "database")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT COUNT(*) FROM pricing.MODEL_RUN")
        ).scalar_one() == 0
        assert connection.execute(
            text("SELECT COUNT(*) FROM pricing.MODEL_MONITOR_VARIANT")
        ).scalar_one() == 4
        assert connection.execute(
            text("SELECT COUNT(*) FROM pricing.V_CURRENT_DEPLOYED_RELATIVITY")
        ).scalar_one() == 0
