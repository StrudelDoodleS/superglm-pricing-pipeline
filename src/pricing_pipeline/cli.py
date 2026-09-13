"""Parse ``pricing-pipeline init`` and ``scaffold`` commands.

Dispatch project setup to ``scaffold.commands`` and report command errors.
Model fitting and publication are exposed through ``notebook.py``.
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable, Sequence
from pathlib import Path


class UserCommandError(Exception):
    """A sanitized analyst-actionable command failure."""


class _ParserExit(Exception):
    def __init__(self, status: int) -> None:
        self.status = status


class _ArgumentParser(argparse.ArgumentParser):
    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            self._print_message(message, sys.stderr)
        raise _ParserExit(status)


_HANDLERS = {
    "init": "pricing_pipeline.scaffold.commands:run_init",
    "scaffold": "pricing_pipeline.scaffold.commands:run_scaffold",
}


def _load_handler(spec: str) -> Callable[[argparse.Namespace], tuple[str, ...]]:
    module_name, function_name = spec.split(":", maxsplit=1)
    return getattr(importlib.import_module(module_name), function_name)


def build_parser() -> argparse.ArgumentParser:
    """Define CLI flags and the Namespace attributes passed to command handlers.

    For example, ``--runtime-module`` becomes ``namespace.runtime_module``.
    ``scaffold.commands._raw_scaffold_options`` merges it with TOML defaults;
    ``scaffold.render.render_notebooks`` maps the resolved value to a template token.
    """

    parser = _ArgumentParser(
        prog="pricing-pipeline",
        description=(
            "Run pricing-pipeline init, edit the config, then scaffold a pricing-model workspace."
        ),
    )
    subcommands = parser.add_subparsers(dest="command")
    init = subcommands.add_parser(
        "init",
        help="create pricing_scaffold.toml and a GitHub Copilot pricing builder agent",
    )
    init.add_argument("--root", type=Path, default=Path("."))
    scaffold = subcommands.add_parser(
        "scaffold",
        help="create the configured standalone notebook workflow",
    )
    scaffold.add_argument("--model-name", required=True)
    scaffold.add_argument("--target-name", required=True)
    scaffold.add_argument("--model-label")
    scaffold.add_argument("--model-type", default="superglm_poisson")
    scaffold.add_argument("--deployment-slot")
    scaffold.add_argument("--package-name")
    scaffold.add_argument("--root", type=Path, default=Path("."))
    scaffold.add_argument("--config", type=Path)
    scaffold.add_argument("--database-mode", choices=("local", "remote"))
    scaffold.add_argument("--runtime-module")
    scaffold.add_argument("--expected-remote-database")
    scaffold.add_argument("--manual-edit-source", choices=("deployed", "latest"))
    scaffold.add_argument(
        "--manual-edit-carry-forward",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    scaffold.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, invoke the selected command handler and print its results.

    ``_HANDLERS`` links the scaffold subcommand to ``commands.run_scaffold``.
    Return an exit code; notebook generation does not execute the generated cells.
    """

    parser = build_parser()
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        namespace = parser.parse_args(arguments)
    except _ParserExit as exc:
        return exc.status
    if namespace.command is None:
        parser.print_help(sys.stderr)
        return 2
    try:
        messages = _load_handler(_HANDLERS[namespace.command])(namespace)
    except UserCommandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - sanitize unexpected command failures at the CLI boundary
        print(
            "error: pricing-pipeline failed unexpectedly; rerun with your normal support logging",
            file=sys.stderr,
        )
        return 1
    for message in messages:
        print(message)
    return 0
