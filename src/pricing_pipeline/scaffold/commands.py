from __future__ import annotations

import argparse
import errno
import os
from pathlib import Path

from pricing_pipeline.cli import UserCommandError
from pricing_pipeline.resources import scaffold_template
from pricing_pipeline.scaffold import legacy

_CONFIG_NAME = "pricing_scaffold.toml"
_SCAFFOLD_COMMAND = (
    "pricing-pipeline scaffold --model-name CLAIM_FREQUENCY --target-name claim_count"
)


def _root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _init_messages(config_path: Path) -> tuple[str, ...]:
    return (
        str(config_path),
        f"Edit {config_path}, then run:",
        _SCAFFOLD_COMMAND,
    )


def _require_project_root(root: Path) -> None:
    pyproject = root / "pyproject.toml"
    if pyproject.is_symlink() or not pyproject.is_file():
        raise UserCommandError(
            f"project root must contain a regular non-symlink pyproject.toml: {pyproject}"
        )


def _validate_existing_config(config_path: Path) -> tuple[str, ...]:
    if config_path.is_symlink() or not config_path.is_file():
        raise UserCommandError(
            f"existing scaffold config must be a regular non-symlink file: {config_path}"
        )
    try:
        legacy.load_scaffold_config(config_path)
    except (TypeError, ValueError) as exc:
        raise UserCommandError(str(exc)) from exc
    return _init_messages(config_path)


def run_init(namespace: argparse.Namespace) -> tuple[str, ...]:
    root = _root(namespace.root)
    _require_project_root(root)
    config_path = root / _CONFIG_NAME
    if config_path.is_symlink() or config_path.exists():
        return _validate_existing_config(config_path)

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if no_follow := getattr(os, "O_NOFOLLOW", 0):
        flags |= no_follow
    try:
        descriptor = os.open(config_path, flags, 0o666)
    except FileExistsError:
        return _validate_existing_config(config_path)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise UserCommandError(
                f"existing scaffold config must be a regular non-symlink file: {config_path}"
            ) from exc
        raise UserCommandError(f"could not create scaffold config {config_path}: {exc}") from exc

    template = scaffold_template().read_bytes()
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(template)
    except OSError as exc:
        raise UserCommandError(f"could not write scaffold config {config_path}: {exc}") from exc
    return _init_messages(config_path)


def _load_installed_config(namespace: argparse.Namespace, root: Path) -> legacy.ScaffoldConfig:
    implicit = namespace.config is None
    config_path = root / _CONFIG_NAME if implicit else Path(namespace.config)
    if implicit and not config_path.is_file():
        raise UserCommandError(
            f"scaffold config does not exist: {config_path}; "
            f"run pricing-pipeline init --root {root}"
        )
    try:
        return legacy.load_scaffold_config(config_path)
    except (TypeError, ValueError) as exc:
        raise UserCommandError(str(exc)) from exc


def _scaffold_options(
    namespace: argparse.Namespace,
    root: Path,
    config: legacy.ScaffoldConfig,
) -> legacy.ScaffoldOptions:
    try:
        database_mode = legacy._database_mode(
            namespace.database_mode if namespace.database_mode is not None else config.database_mode
        )
        runtime_module = legacy._runtime_module(
            namespace.runtime_module
            if namespace.runtime_module is not None
            else config.runtime_module
        )
        expected_remote_database = legacy._expected_remote_database(
            namespace.expected_remote_database
            if namespace.expected_remote_database is not None
            else config.expected_remote_database
        )
        if database_mode == "remote" and not expected_remote_database:
            raise ValueError("expected_remote_database is required when database_mode='remote'")
        manual_edit_source = legacy._manual_edit_source_selector(
            namespace.manual_edit_source
            if namespace.manual_edit_source is not None
            else config.manual_edit_source_selector
        )
        manual_edit_carry_forward = legacy._manual_edit_carry_forward(
            namespace.manual_edit_carry_forward
            if namespace.manual_edit_carry_forward is not None
            else config.manual_edit_carry_forward
        )
    except (TypeError, ValueError) as exc:
        raise UserCommandError(str(exc)) from exc
    return legacy.ScaffoldOptions(
        model_name=namespace.model_name,
        target_name=namespace.target_name,
        model_label=namespace.model_label,
        model_type=namespace.model_type,
        deployment_slot=namespace.deployment_slot,
        package_name=namespace.package_name,
        database_mode=database_mode,
        runtime_module=runtime_module,
        expected_remote_database=expected_remote_database,
        manual_edit_source_selector=manual_edit_source,
        manual_edit_carry_forward=manual_edit_carry_forward,
        root=root,
        force=namespace.force,
    )


def run_scaffold(namespace: argparse.Namespace) -> tuple[str, ...]:
    root = _root(namespace.root)
    config = _load_installed_config(namespace, root)
    options = _scaffold_options(namespace, root, config)
    try:
        result = legacy.scaffold_pricing_model(options)
    except (TypeError, ValueError) as exc:
        raise UserCommandError(str(exc)) from exc
    return tuple(str(path.resolve()) for path in result.created_files)
