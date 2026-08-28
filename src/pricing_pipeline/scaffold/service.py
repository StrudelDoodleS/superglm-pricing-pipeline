from __future__ import annotations

import errno
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pricing_pipeline.scaffold import config
from pricing_pipeline.scaffold.config import ScaffoldOptions
from pricing_pipeline.scaffold.render import render_notebooks

_LEGACY_DEPLOYMENT_NOTEBOOK = "04_model_deployment.ipynb"
_DEPLOYMENT_NOTEBOOK = "06_model_deployment.ipynb"


@dataclass(frozen=True)
class ScaffoldResult:
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


def _reject_managed_ancestor_symlinks(pricing_models_dir: Path, package_dir: Path) -> None:
    for path in (pricing_models_dir, package_dir):
        if path.is_symlink():
            raise ValueError(
                f"cannot write scaffold output: managed path {path.name} is a symbolic link. "
                "Replace the link with a directory, then rerun the scaffold."
            )


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


def scaffold_pricing_model(options: ScaffoldOptions) -> ScaffoldResult:
    resolved = config.resolve_scaffold_options(options)
    pricing_models_dir = resolved.root / "pricing_models"
    package_dir = pricing_models_dir / resolved.package_name
    _reject_managed_ancestor_symlinks(pricing_models_dir, package_dir)
    notebooks = render_notebooks(
        package_name=resolved.package_name,
        model_name=resolved.model_name,
        model_label=resolved.model_label,
        target_name=resolved.target_name,
        model_type=resolved.model_type,
        deployment_slot=resolved.deployment_slot,
        database_mode=resolved.database_mode,
        runtime_module=resolved.runtime_module,
        expected_remote_database=resolved.expected_remote_database,
        manual_edit_source_selector=resolved.manual_edit_source_selector,
        manual_edit_carry_forward=resolved.manual_edit_carry_forward,
    )
    content = {
        package_dir / "__init__.py": f'"""Pricing notebook package for {resolved.model_name}."""\n',
        **{package_dir / filename: source for filename, source in notebooks.items()},
    }
    _reject_output_symlinks(content)
    _reject_invalid_output_types(content)
    migrated_deployment = _migrate_legacy_deployment_notebook(package_dir)
    created = []
    for path, source in content.items():
        if path == migrated_deployment:
            continue
        if path.exists() and not resolved.force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_scaffold_output(path, source)
        created.append(path)
    return ScaffoldResult(package_name=resolved.package_name, created_files=tuple(created))
