"""Keep SQL-only promotion behind notebook write and connection guards."""

from dataclasses import replace

import pytest

from pricing_pipeline import notebook
from pricing_pipeline.infra.config import Settings
from tests import test_sql_champion_review

sql_review_case = test_sql_champion_review.sql_review_case


def _context_and_model(sql_review_case, tmp_path):
    engine, config = sql_review_case
    return (
        notebook.NotebookContext(
            engine=engine,
            settings=Settings(),
            mode="remote",
            write_allowed=True,
            destination="isolated SQL review fixture",
        ),
        notebook.RegisteredModel(model_id=17, config=config, source_root=tmp_path, spec=None),
    )


def test_review_and_list_are_available_without_write_permission(sql_review_case, tmp_path):
    pricing, model = _context_and_model(sql_review_case, tmp_path)
    pricing = replace(pricing, write_allowed=False)
    rows = notebook.list_challengers(pricing, model=model)
    assert rows.package_version.tolist() == [2, 1]
    reviewed = notebook.review_model_version(pricing, model=model, package_version=2)
    assert isinstance(reviewed, notebook.ReviewedModelVersion)
    assert reviewed.rate_package_id == 102
    with pytest.raises(PermissionError, match="Remote writes are disabled"):
        notebook.deploy_model_version(pricing, package=reviewed, reason="Reviewed")


def test_sql_reviewed_promotion_rejects_another_connection(sql_review_case, tmp_path):
    pricing, model = _context_and_model(sql_review_case, tmp_path)
    reviewed = notebook.review_model_version(pricing, model=model, package_version=2)
    other = replace(pricing, engine=object())
    with pytest.raises(ValueError, match="different notebook context"):
        notebook.deploy_model_version(other, package=reviewed, reason="Reviewed")


def test_sql_reviewed_promotion_keeps_explicit_review_identity(
    sql_review_case, tmp_path, monkeypatch
):
    from pricing_pipeline.workbench import champion

    pricing, model = _context_and_model(sql_review_case, tmp_path)
    reviewed = notebook.review_model_version(pricing, model=model, package_version=2)
    calls = []

    def deploy(engine, config, **kwargs):
        calls.append((engine, config, kwargs))
        return "deployed"

    monkeypatch.setattr(champion, "deploy_rate_package", deploy)
    assert (
        notebook.deploy_model_version(
            pricing, package=reviewed, reason="Approved comparison", deployed_by="analyst"
        )
        == "deployed"
    )
    engine, config, options = calls.pop()
    assert engine is pricing.engine and config is model.config
    assert options["rate_package_id"] == 102
    assert options["expected_current_rate_package_id"] is None
    assert options["expected_current_deployment_id"] is None
    assert options["deployment_reason"] == "Approved comparison"
    assert options["deployed_by"] == "analyst"


def test_sql_review_does_not_enable_local_deployment(sql_review_case, tmp_path):
    pricing, model = _context_and_model(sql_review_case, tmp_path)
    local = replace(pricing, mode="local")
    reviewed = notebook.review_model_version(local, model=model, package_version=2)
    with pytest.raises(RuntimeError, match="Remote mode is required"):
        notebook.deploy_model_version(local, package=reviewed, reason="Reviewed")
