"""The registry separates declared revisions, individual fits and deployment roles."""
# ruff: noqa: F811 - pytest resolves the shared fixture by its parameter name.

from pathlib import Path

from sqlalchemy import text

from tests.test_sql_champion_review import _deploy_fixture, sql_review_case  # noqa: F401


def _registry(engine):
    with engine.connect() as connection:
        return (
            connection.execute(
                text(
                    "SELECT * FROM pricing.V_MODEL_REGISTRY ORDER BY deployment_slot, package_version"
                )
            )
            .mappings()
            .all()
        )


def test_registry_includes_never_deployed_models_without_inventing_a_revision(sql_review_case):
    engine, _ = sql_review_case
    rows = _registry(engine)
    assert len(rows) == 2
    assert {row["role"] for row in rows} == {"CHALLENGER"}
    assert all(row["definition_revision"] is None for row in rows)
    assert all(row["deployment_slot"] is None for row in rows)
    assert {row["refit_type"] for row in rows} == {"Analyst fit"}
    assert all(row["published_at"] is not None for row in rows)
    assert "model_version" not in rows[0]


def test_registry_roles_follow_human_deployment_per_slot_without_new_fits(sql_review_case):
    engine, _ = sql_review_case
    deployment = _deploy_fixture(engine, 101)
    _deploy_fixture(engine, 102, "OTHER_SLOT")
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_from_ts='2026-01-01'")
        )
    before = _registry(engine)
    assert {(r["deployment_slot"], r["package_version"], r["role"]) for r in before} == {
        ("TEST_CURRENT", 1, "CHAMPION"),
        ("TEST_CURRENT", 2, "CHALLENGER"),
        ("OTHER_SLOT", 1, "CHALLENGER"),
        ("OTHER_SLOT", 2, "CHAMPION"),
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE pricing.PRICING_MODEL_DEPLOYMENT SET effective_to_ts=CURRENT_TIMESTAMP "
                "WHERE deployment_id=:id"
            ),
            {"id": deployment},
        )
    _deploy_fixture(engine, 102)
    after = _registry(engine)
    assert len(after) == 4
    assert {(r["deployment_slot"], r["package_version"], r["role"]) for r in after} == {
        ("TEST_CURRENT", 1, "FORMER_CHAMPION"),
        ("TEST_CURRENT", 2, "CHAMPION"),
        ("OTHER_SLOT", 1, "CHALLENGER"),
        ("OTHER_SLOT", 2, "CHAMPION"),
    }
    assert {r["model_run_id"] for r in before} == {r["model_run_id"] for r in after}


def test_sql_server_registry_select_matches_offline_results(sql_review_case):
    engine, _ = sql_review_case
    _deploy_fixture(engine, 101)
    migration = Path("src/pricing_pipeline/resources/migrations/V051__model_registry.sql")
    select = migration.read_text().split("\nGO\n", 1)[0].split("\nAS\n", 1)[1]
    # SQLite keeps monitoring tables beside pricing tables. The SELECT is shared SQL.
    select = select.replace("mlops.", "pricing.")
    with engine.connect() as connection:
        server_rows = connection.execute(text(select)).mappings().all()
    expected = {tuple(row.items()) for row in _registry(engine)}
    assert {tuple(row.items()) for row in server_rows} == expected


def test_registry_distinguishes_grouped_fits_from_coefficient_edits(sql_review_case):
    engine, _ = sql_review_case
    with engine.begin() as connection:
        connection.execute(
            text("""UPDATE pricing.MODEL_RUN SET model_kind=
            CASE model_run_id WHEN '1' THEN 'ROUTINE_EDIT' ELSE 'EDITOR_EDIT' END""")
        )
    assert [row["refit_type"] for row in _registry(engine)] == ["Grouped fit", "Manual adjustment"]


def test_registry_and_review_report_package_publication_time(sql_review_case):
    from pricing_pipeline.workbench.champion import review_model_version

    engine, config = sql_review_case
    with engine.begin() as connection:
        connection.execute(text("UPDATE pricing.MODEL_RUN SET created_ts='2026-08-01 09:00:00'"))
        connection.execute(
            text("UPDATE pricing.PRICING_RATE_PACKAGE SET created_ts='2026-08-02 10:00:00'")
        )
    assert {row["published_at"] for row in _registry(engine)} == {"2026-08-02 10:00:00"}
    reviewed = review_model_version(engine, model_config=config, model_id=17, package_version=1)
    assert reviewed.published_at == "2026-08-02 10:00:00"
