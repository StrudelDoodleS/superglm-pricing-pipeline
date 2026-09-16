from __future__ import annotations

import importlib.util
import socket
import sys

import pytest

from pricing_pipeline import cli


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root = tmp_path / "demo"
    assert cli.main(["demo", "--root", str(root)]) == 0
    monkeypatch.syspath_prepend(str(root))
    monkeypatch.delitem(sys.modules, "demo_sql_runtime", raising=False)
    spec = importlib.util.spec_from_file_location("generated_demo_setup", root / "setup_demo.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("demo_sql_runtime", None)


def test_setup_preserves_credentials_and_chooses_an_unused_port(setup):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        setup.DEFAULT_SQL_PORT = occupied.getsockname()[1]
        first = setup.ensure_environment()
        assert int(first["DEMO_SQL_PORT"]) != setup.DEFAULT_SQL_PORT
        assert first["MSSQL_SA_PASSWORD"]
        before = (setup.ROOT / ".env").read_bytes()
        assert setup.ensure_environment() == first
        assert (setup.ROOT / ".env").read_bytes() == before


def test_setup_explains_missing_driver_before_creating_state(setup, monkeypatch):
    monkeypatch.setattr(setup.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(RuntimeError, match=r"pymssql.*\[demo\]"):
        setup.require_demo_dependencies()
    assert not (setup.ROOT / ".env").exists()


def test_setup_reports_missing_docker_without_starting_another_service(setup, monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("No server")

    monkeypatch.setattr(setup.socket, "create_connection", unavailable)
    monkeypatch.setattr(setup.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="Docker is unavailable"):
        setup.start_server_if_needed(14339)


def test_docker_uses_the_runtime_credentials_and_port_despite_shell_overrides(setup, monkeypatch):
    settings = setup.ensure_environment()
    monkeypatch.setenv("MSSQL_SA_PASSWORD", "unrelated-shell-password")
    monkeypatch.setenv("DEMO_SQL_PORT", "12345")
    calls = []

    def unavailable(*args, **kwargs):
        raise OSError("No server")

    monkeypatch.setattr(setup.socket, "create_connection", unavailable)
    monkeypatch.setattr(setup.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(setup.subprocess, "run", lambda *args, **kwargs: calls.append(kwargs))

    setup.start_server_if_needed(int(settings["DEMO_SQL_PORT"]))

    assert len(calls) == 1
    assert calls[0]["env"]["MSSQL_SA_PASSWORD"] == settings["MSSQL_SA_PASSWORD"]
    assert calls[0]["env"]["DEMO_SQL_PORT"] == settings["DEMO_SQL_PORT"]
