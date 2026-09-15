from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import create_engine, event

from pricing_pipeline.scaffold.config import ScaffoldOptions
from pricing_pipeline.scaffold.service import scaffold_pricing_model


def _deployment_code_cells(tmp_path):
    scaffold_pricing_model(
        ScaffoldOptions(model_name="REVIEW_MODEL", target_name="target", root=tmp_path)
    )
    path = tmp_path / "pricing_models" / "review_model" / "06_model_deployment.ipynb"
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return ["".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"]


def _deployment_cells(tmp_path):
    code = _deployment_code_cells(tmp_path)
    review = next(cell for cell in code if "reviewed =" in cell and "package_version=" in cell)
    promote = next(cell for cell in code if "deployment = deploy_model_version(" in cell)
    return review, promote


def _reject_artifact_load(*args, **kwargs):
    pytest.fail("Deployment review must read SQL without loading a local model artifact")


def _reject_promotion(*args, **kwargs):
    pytest.fail("The notebook must require an explicit, unchanged reviewed package selection")


def test_deployment_requires_an_explicit_version_before_review(tmp_path):
    review, _ = _deployment_cells(tmp_path)
    namespace = {
        "PACKAGE_VERSION": None,
        "deployable": pd.DataFrame({"package_version": [9, 4]}),
        "pricing": object(),
        "model": object(),
        "load_model_version": _reject_artifact_load,
        "review_model_version": _reject_promotion,
        "reviewed": object(),
    }

    with pytest.raises(ValueError, match="PACKAGE_VERSION"):
        exec(compile(review, "06:review", "exec"), namespace)  # noqa: S102

    assert namespace["reviewed"] is None


@dataclass(frozen=True)
class _SqlReview:
    package_version: int
    summary: pd.DataFrame
    metrics: pd.DataFrame


def test_deployment_records_a_reason_after_sql_review_then_promotes(tmp_path):
    code = _deployment_code_cells(tmp_path)
    settings = code[0]
    reason_cell = next(cell for cell in code if 'DEPLOYMENT_REASON = ""' in cell)
    review_cell = next(cell for cell in code if "reviewed =" in cell and "package_version=" in cell)
    promote_cell = next(cell for cell in code if "deployment = deploy_model_version(" in cell)
    summary = pd.DataFrame({"package_version": [4], "current_rate_package_id": [11]})
    metrics = pd.DataFrame({"metric_name": ["deviance"], "metric_value": [0.8]})
    reviewed = _SqlReview(package_version=4, summary=summary, metrics=metrics)
    pricing = SimpleNamespace(engine=create_engine("sqlite://"))
    model = object()
    displayed = []
    promoted = []
    disposed = []
    on_dispose = disposed.append
    event.listen(pricing.engine, "engine_disposed", on_dispose)

    def review_sql(selected_pricing, *, model, package_version):
        assert selected_pricing is pricing
        assert package_version == 4
        return reviewed

    def promote_sql(selected_pricing, *, package, reason):
        assert selected_pricing is pricing
        promoted.append((package, reason))
        return {"rate_package_id": 14}

    namespace = {
        "deployable": pd.DataFrame({"package_version": [9, 4]}),
        "pricing": pricing,
        "model": model,
        "load_model_version": _reject_artifact_load,
        "review_model_version": review_sql,
        "deploy_model_version": promote_sql,
        "display": displayed.append,
    }
    try:
        exec(  # noqa: S102 - apply the analyst's package choice in the real settings cell
            compile(
                settings.replace("PACKAGE_VERSION = None", "PACKAGE_VERSION = 4"),
                "06:settings",
                "exec",
            ),
            namespace,
        )
        exec(compile(review_cell, "06:review", "exec"), namespace)  # noqa: S102
        assert namespace["reviewed"] is reviewed
        assert len(displayed) == 2
        pd.testing.assert_frame_equal(displayed[0], summary)
        pd.testing.assert_frame_equal(displayed[1], metrics)
        assert promoted == []

        exec(  # noqa: S102 - apply a decision after review without rerunning model settings
            compile(
                reason_cell.replace(
                    'DEPLOYMENT_REASON = ""',
                    'DEPLOYMENT_REASON = "Approved after comparison with the current champion"',
                ),
                "06:reason",
                "exec",
            ),
            namespace,
        )
        assert namespace["reviewed"] is reviewed
        exec(compile(promote_cell, "06:promote", "exec"), namespace)  # noqa: S102
    finally:
        event.remove(pricing.engine, "engine_disposed", on_dispose)
        pricing.engine.dispose()

    assert disposed == [pricing.engine]
    assert promoted == [(reviewed, "Approved after comparison with the current champion")]
    assert namespace["deployment"] == {"rate_package_id": 14}

    exec(  # noqa: S102 - changing package settings must invalidate the previous review
        compile(
            settings.replace("PACKAGE_VERSION = None", "PACKAGE_VERSION = 9"), "06:settings", "exec"
        ),
        namespace,
    )
    assert namespace["reviewed"] is None
    with pytest.raises(ValueError, match="review"):
        exec(compile(promote_cell, "06:promote", "exec"), namespace)  # noqa: S102
    assert len(promoted) == 1


def test_deployment_rejects_a_version_changed_after_review(tmp_path):
    _, promote = _deployment_cells(tmp_path)
    pricing = SimpleNamespace(engine=create_engine("sqlite://"))
    namespace = {
        "PACKAGE_VERSION": 9,
        "DEPLOYMENT_REASON": "Approved package 4",
        "pricing": pricing,
        "reviewed": _SqlReview(4, pd.DataFrame(), pd.DataFrame()),
        "deploy_model_version": _reject_promotion,
    }
    try:
        with pytest.raises(ValueError, match="PACKAGE_VERSION.*review"):
            exec(compile(promote, "06:promote", "exec"), namespace)  # noqa: S102
    finally:
        pricing.engine.dispose()
