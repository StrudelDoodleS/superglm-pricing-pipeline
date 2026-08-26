from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Callable, Sequence


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
    parser = _ArgumentParser(
        prog="pricing-pipeline",
        description="pricing-pipeline init creates pricing_model.toml, then stops for review.",
    )
    subcommands = parser.add_subparsers(dest="command")
    for name, help_text in (
        ("init", "create pricing_model.toml, then stop for review"),
        ("scaffold", "create the configured standalone notebook workflow"),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--root", type=str, default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
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
    except Exception:
        print(
            "error: pricing-pipeline failed unexpectedly; rerun with your normal support logging",
            file=sys.stderr,
        )
        return 1
    for message in messages:
        print(message)
    return 0
