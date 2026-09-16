"""Copy the installed burn-cost demo into a new directory.

The command creates files only. The generated setup_demo.py starts SQL Server
and prepares its dedicated database when the user runs it.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from importlib.resources.abc import Traversable
from pathlib import Path
from uuid import uuid4

from pricing_pipeline.cli import UserCommandError
from pricing_pipeline.resources import demo_root, scaffold_root


def _command(*arguments: str) -> str:
    return subprocess.list2cmdline(arguments) if os.name == "nt" else shlex.join(arguments)


def _copy_resources(source: Traversable, destination: Path) -> None:
    for item in sorted(source.iterdir(), key=lambda value: value.name):
        if item.name == "__pycache__" or item.name.endswith(".pyc"):
            continue
        path = destination / item.name
        if item.is_dir():
            path.mkdir()
            _copy_resources(item, path)
        elif item.is_file():
            with path.open("xb") as handle:
                handle.write(item.read_bytes())


def run_demo(namespace: argparse.Namespace) -> tuple[str, ...]:
    """Generate a clean demo and print commands using this Python environment."""
    root = Path(namespace.root).expanduser().absolute()
    if root.exists() or root.is_symlink():
        raise UserCommandError(f"demo needs a new directory; existing files are preserved: {root}")
    try:
        root.mkdir(parents=True)
        _copy_resources(demo_root(), root)
        compose = root / "compose.yaml"
        compose.write_text(
            compose.read_text(encoding="utf-8").replace("__PROJECT_ID__", uuid4().hex[:12]),
            encoding="utf-8",
        )
        agents = root / ".github" / "agents"
        agents.mkdir(parents=True)
        for name in ("pricing-builder.agent.md", "pricing-developer.agent.md"):
            with (agents / name).open("xb") as handle:
                handle.write(scaffold_root().joinpath(name).read_bytes())
        setup = _command(sys.executable, str(root / "setup_demo.py"))
        jupyter = _command(sys.executable, "-m", "jupyter", "lab", "--notebook-dir", str(root))
        stop = _command(sys.executable, str(root / "setup_demo.py"), "--stop")
        readme = root / "README.md"
        text = readme.read_text(encoding="utf-8")
        for token, value in (
            ("__SETUP_COMMAND__", setup),
            ("__JUPYTER_COMMAND__", jupyter),
            ("__STOP_COMMAND__", stop),
        ):
            text = text.replace(token, value)
        readme.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise UserCommandError(f"could not create demo at {root}: {exc}") from exc
    return (
        f"Created SQL Server demo: {root}",
        "Use the demo extra in this Python environment and start Docker with Linux containers.",
        "Prepare the database and notebook kernel:",
        setup,
        "Then select the Pricing SQL demo kernel in VS Code, or start Jupyter:",
        jupyter,
        f"Instructions: {root / 'README.md'}",
    )
