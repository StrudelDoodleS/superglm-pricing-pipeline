from __future__ import annotations

import argparse
from pathlib import Path

from pricing_pipeline.scaffold.config import (
    ScaffoldConfig,
    ScaffoldOptions,
    _database_mode,
    _expected_remote_database,
    _manual_edit_carry_forward,
    _manual_edit_source_selector,
    _runtime_module,
    load_scaffold_config,
)
from pricing_pipeline.scaffold.render import NOTEBOOK_NAMES, render_notebooks
from pricing_pipeline.scaffold.service import ScaffoldResult, scaffold_pricing_model

__all__ = (
    "ScaffoldConfig",
    "ScaffoldOptions",
    "ScaffoldResult",
    "load_scaffold_config",
    "main",
    "parse_args",
    "scaffold_pricing_model",
)

_NOTEBOOK_NAMES = NOTEBOOK_NAMES
_notebooks = render_notebooks

_DEFAULT_CONFIG_NAME = "pricing_scaffold.toml"


def parse_args(argv: list[str] | None = None) -> ScaffoldOptions:
    parser = argparse.ArgumentParser(description="Create a pricing-model notebook workflow.")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--target-name", required=True)
    parser.add_argument("--model-label")
    parser.add_argument("--model-type", default="superglm_poisson")
    parser.add_argument("--deployment-slot")
    parser.add_argument("--package-name")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--config",
        type=Path,
        help=(
            "TOML defaults file; when omitted, <root>/pricing_scaffold.toml is loaded if present"
        ),
    )
    parser.add_argument(
        "--database-mode",
        choices=("local", "remote"),
        help="override notebook_defaults.database_mode",
    )
    parser.add_argument(
        "--runtime-module",
        help="override notebook_defaults.runtime_module",
    )
    parser.add_argument(
        "--expected-remote-database",
        help="override notebook_defaults.expected_remote_database",
    )
    parser.add_argument(
        "--manual-edit-source",
        choices=("deployed", "latest"),
        help="override manual_edit_defaults.source_selector",
    )
    parser.add_argument(
        "--manual-edit-carry-forward",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="override manual_edit_defaults.carry_forward",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    auto_config = args.root / _DEFAULT_CONFIG_NAME
    config_path = args.config if args.config is not None else auto_config
    if args.config is not None or config_path.is_file():
        try:
            config = load_scaffold_config(config_path)
        except (TypeError, ValueError) as exc:
            parser.error(str(exc))
    else:
        config = ScaffoldConfig()
    try:
        database_mode = _database_mode(
            args.database_mode if args.database_mode is not None else config.database_mode
        )
        runtime_module = _runtime_module(
            args.runtime_module if args.runtime_module is not None else config.runtime_module
        )
        expected_remote_database = _expected_remote_database(
            args.expected_remote_database
            if args.expected_remote_database is not None
            else config.expected_remote_database
        )
        if database_mode == "remote" and not expected_remote_database:
            raise ValueError("expected_remote_database is required when database_mode='remote'")
        manual_edit_source_selector = _manual_edit_source_selector(
            args.manual_edit_source
            if args.manual_edit_source is not None
            else config.manual_edit_source_selector
        )
        manual_edit_carry_forward = _manual_edit_carry_forward(
            args.manual_edit_carry_forward
            if args.manual_edit_carry_forward is not None
            else config.manual_edit_carry_forward
        )
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    return ScaffoldOptions(
        model_name=args.model_name,
        target_name=args.target_name,
        model_label=args.model_label,
        model_type=args.model_type,
        deployment_slot=args.deployment_slot,
        package_name=args.package_name,
        database_mode=database_mode,
        runtime_module=runtime_module,
        expected_remote_database=expected_remote_database,
        manual_edit_source_selector=manual_edit_source_selector,
        manual_edit_carry_forward=manual_edit_carry_forward,
        root=args.root,
        force=args.force,
    )


def main(argv: list[str] | None = None) -> int:
    result = scaffold_pricing_model(parse_args(argv))
    for path in result.created_files:
        print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
