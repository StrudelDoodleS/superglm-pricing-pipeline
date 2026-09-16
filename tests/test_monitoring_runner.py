from __future__ import annotations

import importlib.util
import logging

import pandas as pd
import pytest


def _runner():
    assert importlib.util.find_spec("pricing_pipeline.monitoring_runner") is not None
    from pricing_pipeline.monitoring_runner import run_monitoring_script

    return run_monitoring_script


def _report():
    from pricing_pipeline.modeling.monitoring.batch import MonitoringReport

    return MonitoringReport(
        manifest_id="new_snapshot_20260915",
        runs=pd.DataFrame(
            {"variant": ["STATIC_SCORE", "FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"]}
        ),
        metrics=pd.DataFrame(),
        issues=pd.DataFrame(),
        drift=pd.DataFrame(),
    )


def test_script_records_progress_and_success_in_new_log(tmp_path, capsys):
    run_script = _runner()

    def job():
        logging.getLogger("pricing_pipeline.monitoring").info("Starting FROZEN_REFIT")
        return _report()

    assert run_script(job, log_directory=tmp_path / "logs") == 0
    logs = list((tmp_path / "logs").glob("*.log"))
    assert len(logs) == 1
    output = logs[0].read_text()
    assert "Starting FROZEN_REFIT" in output
    assert "new_snapshot_20260915" in output
    assert "FULL_ADAPTIVE" in output
    assert str(logs[0]) in capsys.readouterr().err


def test_script_failure_has_nonzero_exit_and_traceback(tmp_path, capsys):
    run_script = _runner()

    def job():
        raise ValueError("driver_age has no observations in the saved spline domain")

    assert run_script(job, log_directory=tmp_path) == 1
    output = next(tmp_path.glob("*.log")).read_text()
    assert "Traceback" in output
    assert "driver_age has no observations" in output
    assert "Monitoring complete" not in output
    assert "driver_age" in capsys.readouterr().err


def test_script_rejects_missing_report(tmp_path):
    assert _runner()(lambda: None, log_directory=tmp_path) == 1
    assert "MonitoringReport" in next(tmp_path.glob("*.log")).read_text()


def test_script_interrupt_is_reported_as_failure(tmp_path):
    run_script = _runner()

    def job():
        raise KeyboardInterrupt

    assert run_script(job, log_directory=tmp_path) == 130
    assert "interrupted" in next(tmp_path.glob("*.log")).read_text().lower()


def test_script_does_not_run_when_log_directory_cannot_be_created(tmp_path, capsys):
    path = tmp_path / "regular_file"
    path.write_text("keep")

    def job():
        pytest.fail("the job must not start without its execution log")

    assert _runner()(job, log_directory=path) == 2
    assert path.read_text() == "keep"
    assert "log" in capsys.readouterr().err.lower()


def test_script_restores_logger_and_keeps_separate_logs_after_failure(tmp_path):
    logger = logging.getLogger("pricing_pipeline.monitoring")
    original = (tuple(logger.handlers), logger.level, logger.propagate)

    def fail():
        raise ValueError("source query needs configuration")

    run_script = _runner()
    for _ in range(2):
        assert run_script(fail, log_directory=tmp_path) == 1
        assert (tuple(logger.handlers), logger.level, logger.propagate) == original
    logs = list(tmp_path.glob("*.log"))
    assert len(logs) == 2
    assert all(path.read_text().count("Monitoring failed") == 1 for path in logs)


def test_notebook_monitoring_blocks_writes_before_loading_or_locking(tmp_path):
    from pricing_pipeline import notebook
    from pricing_pipeline.infra.config import Settings

    api = getattr(notebook, "run_monitoring", None)
    assert callable(api)
    pricing = notebook.NotebookContext(
        engine=None,
        settings=Settings(),
        mode="remote",
        write_allowed=False,
        destination="read only",
    )
    with pytest.raises(PermissionError, match="Remote writes are disabled"):
        api(pricing, model=None, dataset=None)
    assert list(tmp_path.iterdir()) == []


def test_notebook_monitoring_releases_lock_when_baseline_loading_fails(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from pricing_pipeline import notebook
    from pricing_pipeline.infra.config import Settings
    from pricing_pipeline.infra.file_lock import exclusive_file_lock

    api = getattr(notebook, "run_monitoring", None)
    assert callable(api)
    pricing = notebook.NotebookContext(
        engine=None, settings=Settings(), mode="local", write_allowed=True, destination="test"
    )

    def unavailable(*args, **kwargs):
        raise LookupError("No deployed baseline")

    monkeypatch.setattr(notebook, "load_monitoring_baseline", unavailable)
    model = SimpleNamespace(source_root=tmp_path)
    with pytest.raises(LookupError, match="No deployed baseline"):
        api(pricing, model=model, dataset=None)
    lock = tmp_path / ".local" / "monitoring.lock"
    assert lock.is_file()
    with exclusive_file_lock(lock):
        assert lock.is_file()


def test_notebook_monitoring_publishes_challengers_with_the_connected_model(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from pricing_pipeline import notebook
    from pricing_pipeline.infra.config import Settings
    from pricing_pipeline.modeling.monitoring import batch
    from pricing_pipeline.models.config import ModelBuildConfig

    pricing = notebook.NotebookContext(
        engine=object(), settings=Settings(), mode="local", write_allowed=True, destination="test"
    )
    model = SimpleNamespace(
        source_root=tmp_path,
        model_id=17,
        config=ModelBuildConfig(
            model_name="BURN_COST",
            model_label="Burn cost",
            model_type="superglm",
            target_name="burn_cost",
            deployment_slot="BURN_COST_UAT",
        ),
    )
    baseline, dataset, report = object(), object(), _report()
    monkeypatch.setattr(notebook, "load_monitoring_baseline", lambda *a, **kw: baseline)

    def batch_run(engine, loaded, fresh, **options):
        assert (engine, loaded, fresh) == (pricing.engine, baseline, dataset)
        publication = options["publication"]
        assert publication.settings is pricing.settings
        assert publication.model_config is model.config
        assert publication.model_id == 17
        assert options["target_column"] == "burn_cost"
        return report

    monkeypatch.setattr(batch, "run_monitoring_batch", batch_run)
    assert notebook.run_monitoring(pricing, model=model, dataset=dataset) is report


def test_notebook_monitoring_serializes_runs_for_the_same_model(tmp_path, monkeypatch):
    from threading import Event, Thread
    from types import SimpleNamespace

    from pricing_pipeline import notebook
    from pricing_pipeline.infra.config import Settings

    first_entered, second_started, second_entered, release = (Event() for _ in range(4))
    calls, errors = [], []

    def baseline(*args, **kwargs):
        calls.append(None)
        if len(calls) == 1:
            first_entered.set()
            assert release.wait(5)
        else:
            second_entered.set()
        raise LookupError("baseline unavailable")

    monkeypatch.setattr(notebook, "load_monitoring_baseline", baseline)
    pricing = notebook.NotebookContext(
        engine=None, settings=Settings(), mode="local", write_allowed=True, destination="test"
    )
    model = SimpleNamespace(source_root=tmp_path)

    def invoke(*, second=False):
        if second:
            second_started.set()
        try:
            notebook.run_monitoring(pricing, model=model, dataset=None)
        except Exception as exc:  # noqa: BLE001 - collect thread failures for assertions below
            errors.append(exc)

    first = Thread(target=invoke, daemon=True)
    second = Thread(target=invoke, kwargs={"second": True}, daemon=True)
    first.start()
    try:
        assert first_entered.wait(5)
        second.start()
        assert second_started.wait(5)
        assert not second_entered.wait(0.15)
    finally:
        release.set()
        first.join(5)
        if second.ident is not None:
            second.join(5)
    assert second_entered.is_set()
    assert len(errors) == 2 and all(isinstance(exc, LookupError) for exc in errors)
