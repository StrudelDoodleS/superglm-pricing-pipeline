"""Implement CLI init and scaffold requests using resolved project options.

Initialize the config and builder-agent files, combine command options with
TOML defaults, then call the scaffold filesystem service.
"""

from __future__ import annotations

import argparse
import errno
import os
from pathlib import Path

from pricing_pipeline.cli import UserCommandError
from pricing_pipeline.resources import scaffold_root, scaffold_template
from pricing_pipeline.scaffold import config, service

_CONFIG_NAME = "pricing_scaffold.toml"
_AGENT_NAME = "pricing-builder.agent.md"
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
        f"Or select Pricing builder in Copilot: {config_path.parent / '.github/agents' / _AGENT_NAME}",
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
        config.load_scaffold_config(config_path)
    except (TypeError, ValueError) as exc:
        raise UserCommandError(str(exc)) from exc
    return _init_messages(config_path)


def _init_config(root: Path) -> tuple[str, ...]:
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


def _validate_agent_path(root: Path) -> Path:
    for directory in (root / ".github", root / ".github/agents"):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise UserCommandError(f"agent parent must be a non-symlink directory: {directory}")
    path = root / ".github/agents" / _AGENT_NAME
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise UserCommandError(f"existing agent must be a regular non-symlink file: {path}")
    return path


def run_init(namespace: argparse.Namespace) -> tuple[str, ...]:
    """Seed project config and the builder agent from installed resources.

    Preserve existing files. Notebook creation happens later in ``run_scaffold``.
    """

    root = _root(namespace.root)
    _require_project_root(root)
    agent_path = _validate_agent_path(root)
    messages = _init_config(root)
    try:
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        _validate_agent_path(root)
        # Exclusive creation preserves an agent the analyst has already edited.
        template = scaffold_root().joinpath(_AGENT_NAME).read_bytes()
        try:
            with agent_path.open("xb") as handle:
                handle.write(template)
        except FileExistsError:
            _validate_agent_path(root)
    except OSError as exc:
        raise UserCommandError(f"could not create builder agent {agent_path}: {exc}") from exc
    return messages


def _load_installed_config(namespace: argparse.Namespace, root: Path) -> config.ScaffoldConfig:
    implicit = namespace.config is None
    config_path = root / _CONFIG_NAME if implicit else Path(namespace.config)
    if implicit and not config_path.is_file():
        raise UserCommandError(
            f"scaffold config does not exist: {config_path}; "
            f"run pricing-pipeline init --root {root}"
        )
    try:
        return config.load_scaffold_config(config_path)
    except (TypeError, ValueError) as exc:
        raise UserCommandError(str(exc)) from exc


def _raw_scaffold_options(
    namespace: argparse.Namespace,
    root: Path,
    scaffold_config: config.ScaffoldConfig,
) -> config.ScaffoldOptions:
    """Merge parsed CLI arguments with loaded TOML defaults.

    An explicit CLI value wins; ``None`` means use the corresponding config value.
    For example, ``namespace.runtime_module`` overrides
    ``scaffold_config.runtime_module``. The result still needs
    ``config.resolve_scaffold_options`` before rendering.
    """

    return config.ScaffoldOptions(
        model_name=namespace.model_name,
        target_name=namespace.target_name,
        model_label=namespace.model_label,
        model_type=namespace.model_type,
        deployment_slot=namespace.deployment_slot,
        package_name=namespace.package_name,
        database_mode=(
            namespace.database_mode
            if namespace.database_mode is not None
            else scaffold_config.database_mode
        ),
        runtime_module=(
            namespace.runtime_module
            if namespace.runtime_module is not None
            else scaffold_config.runtime_module
        ),
        expected_remote_database=(
            namespace.expected_remote_database
            if namespace.expected_remote_database is not None
            else scaffold_config.expected_remote_database
        ),
        manual_edit_source_selector=(
            namespace.manual_edit_source
            if namespace.manual_edit_source is not None
            else scaffold_config.manual_edit_source_selector
        ),
        manual_edit_carry_forward=(
            namespace.manual_edit_carry_forward
            if namespace.manual_edit_carry_forward is not None
            else scaffold_config.manual_edit_carry_forward
        ),
        root=root,
        force=namespace.force,
    )


def run_scaffold(namespace: argparse.Namespace) -> tuple[str, ...]:
    """Connect CLI input to notebook creation.

    Load TOML, merge CLI overrides into ``ScaffoldOptions``, validate them into
    ``ResolvedScaffoldOptions``, then call
    ``service.scaffold_resolved_pricing_model`` to render and write the notebooks.
    Return the created paths for ``cli.main`` to print.
    """

    root = _root(namespace.root)
    _require_project_root(root)
    scaffold_config = _load_installed_config(namespace, root)
    options = _raw_scaffold_options(namespace, root, scaffold_config)
    try:
        resolved = config.resolve_scaffold_options(options)
        result = service.scaffold_resolved_pricing_model(resolved)
    except IsADirectoryError as exc:
        managed_root = root / "pricing_models"
        raise UserCommandError(
            f"cannot write scaffold output under {managed_root}: "
            "a managed output leaf is a directory; replace or remove it, then rerun"
        ) from exc
    except (FileExistsError, NotADirectoryError) as exc:
        managed_root = root / "pricing_models"
        raise UserCommandError(
            f"cannot create scaffold output under {managed_root}: "
            "each managed path must be a directory"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise UserCommandError(str(exc)) from exc
    return tuple(str(path.resolve()) for path in result.created_files)
