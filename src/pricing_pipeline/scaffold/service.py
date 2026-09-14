"""Create the model directory and write rendered notebook files.

Check output collisions and symlinks, handle the older deployment notebook
name, and apply the requested overwrite policy.
"""

from __future__ import annotations

import errno
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pricing_pipeline.resources import scaffold_root
from pricing_pipeline.scaffold import config
from pricing_pipeline.scaffold.config import ResolvedScaffoldOptions, ScaffoldOptions
from pricing_pipeline.scaffold.render import render_notebooks

_LEGACY_DEPLOYMENT_NOTEBOOK = "04_model_deployment.ipynb"
_DEPLOYMENT_NOTEBOOK = "06_model_deployment.ipynb"


@dataclass(frozen=True)
class ScaffoldResult:
    """The generated package name and paths written by this scaffold call."""

    package_name: str
    created_files: tuple[Path, ...]


def _migrate_legacy_deployment_notebook(package_dir: Path) -> Path | None:
    legacy_path = package_dir / _LEGACY_DEPLOYMENT_NOTEBOOK
    deployment_path = package_dir / _DEPLOYMENT_NOTEBOOK
    if legacy_path.is_symlink():
        raise ValueError(
            f"cannot upgrade legacy notebook {legacy_path.name}: symbolic links are not supported. "
            "Resolve the legacy path manually, then rerun the scaffold."
        )
    if not legacy_path.exists():
        return None
    if not legacy_path.is_file():
        raise ValueError(
            f"cannot upgrade legacy notebook {legacy_path.name}: expected a regular file. "
            "Resolve the legacy path manually, then rerun the scaffold."
        )
    conflict_message = (
        f"cannot upgrade legacy notebook {legacy_path.name}: {deployment_path.name} already exists. "
        "Resolve the two deployment notebooks manually, remove "
        f"{legacy_path.name}, then rerun the scaffold; --force will not overwrite either notebook."
    )
    if deployment_path.exists() or deployment_path.is_symlink():
        raise ValueError(conflict_message)
    try:
        os.link(legacy_path, deployment_path, follow_symlinks=False)
    except FileExistsError as exc:
        raise ValueError(conflict_message) from exc
    except OSError as exc:
        raise ValueError(
            f"cannot safely upgrade legacy notebook {legacy_path.name} to {deployment_path.name}: {exc}. "
            "Move the notebook manually, then rerun the scaffold."
        ) from exc
    legacy_path.unlink()
    return deployment_path


def _reject_output_symlinks(content: Mapping[Path, str]) -> None:
    for path in content:
        if path.is_symlink():
            raise ValueError(
                f"cannot write scaffold output {path.name}: symbolic links are not supported. "
                "Replace the link with a regular file, then rerun the scaffold."
            )


def _reject_invalid_output_types(content: Mapping[Path, str]) -> None:
    for path in content:
        if path.exists() and not path.is_file():
            raise ValueError(
                f"cannot write scaffold output {path}: existing output is a directory or other "
                "non-regular path; output must be a regular file. Replace or remove it, then "
                "rerun the scaffold."
            )


def _validate_managed_directories(*paths: Path) -> None:
    for path in paths:
        if path.is_symlink():
            raise ValueError(
                f"cannot write scaffold output: managed path {path.name} is a symbolic link. "
                "Replace the link with a directory, then rerun the scaffold."
            )
        if path.exists() and not path.is_dir():
            raise ValueError(f"cannot write scaffold output: managed path {path} must be a directory")


def _write_scaffold_output(path: Path, source: str) -> None:
    no_follow = getattr(os, "O_NOFOLLOW", None)
    if no_follow is None:
        raise RuntimeError("scaffold output writes require a no-follow filesystem operation")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | no_follow
    try:
        descriptor = os.open(path, flags, 0o666)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(
                f"cannot write scaffold output {path.name}: symbolic links are not supported. "
                "Replace the link with a regular file, then rerun the scaffold."
            ) from exc
        raise
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(source)


def scaffold_resolved_pricing_model(options: ResolvedScaffoldOptions) -> ScaffoldResult:
    """Forward validated notebook values to the renderer, then write its output.

    Pass the same resolved options record to ``render_notebooks``. Its token
    map reads the fields directly. ``root`` and ``force`` control file creation
    here; they are not notebook template values. Existing notebooks are skipped
    unless forced.
    """

    pricing_models_dir = options.root / "pricing_models"
    package_dir = pricing_models_dir / options.package_name
    sql_dir = package_dir / "sql"
    _validate_managed_directories(pricing_models_dir, package_dir, sql_dir)
    notebooks = render_notebooks(options)
    content = {
        package_dir / "__init__.py": f'"""Pricing notebook package for {options.model_name}."""\n',
        **{package_dir / filename: source for filename, source in notebooks.items()},
        sql_dir / "README.md": scaffold_root().joinpath("sql", "README.md").read_text(
            encoding="utf-8"
        ),
    }
    _reject_output_symlinks(content)
    _reject_invalid_output_types(content)
    migrated_deployment = _migrate_legacy_deployment_notebook(package_dir)
    created = []
    for path, source in content.items():
        if path == migrated_deployment:
            continue
        if path.exists() and not options.force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_scaffold_output(path, source)
        created.append(path)
    return ScaffoldResult(package_name=options.package_name, created_files=tuple(created))


def scaffold_pricing_model(options: ScaffoldOptions) -> ScaffoldResult:
    """Generate notebooks from Python options without loading project TOML.

    Validate the supplied ``ScaffoldOptions`` and call the same service used by
    the CLI. CLI/TOML precedence is implemented in ``commands.run_scaffold``.
    """

    return scaffold_resolved_pricing_model(config.resolve_scaffold_options(options))
