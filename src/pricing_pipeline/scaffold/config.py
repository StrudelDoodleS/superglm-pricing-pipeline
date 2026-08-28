from __future__ import annotations

import keyword
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_PYTHON_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MODEL_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_DOTTED_MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_DEFAULT_CONFIG_NAME = "pricing_scaffold.toml"
_CONFIG_SECTION = "notebook_defaults"
_MANUAL_EDIT_CONFIG_SECTION = "manual_edit_defaults"
_CONFIG_KEYS = frozenset(
    {
        "database_mode",
        "runtime_module",
        "expected_remote_database",
    }
)


@dataclass(frozen=True)
class ScaffoldOptions:
    model_name: str
    target_name: str
    model_label: str | None = None
    model_type: str = "superglm_poisson"
    deployment_slot: str | None = None
    package_name: str | None = None
    database_mode: str = "local"
    runtime_module: str | None = None
    expected_remote_database: str = ""
    manual_edit_source_selector: str = "deployed"
    manual_edit_carry_forward: bool = True
    root: Path = Path(".")
    force: bool = False


@dataclass(frozen=True)
class ResolvedScaffoldOptions:
    model_name: str
    target_name: str
    model_label: str
    model_type: str
    deployment_slot: str
    package_name: str
    database_mode: str
    runtime_module: str | None
    expected_remote_database: str
    manual_edit_source_selector: str
    manual_edit_carry_forward: bool
    root: Path
    force: bool


@dataclass(frozen=True)
class ScaffoldConfig:
    database_mode: str = "local"
    runtime_module: str | None = None
    expected_remote_database: str = ""
    manual_edit_source_selector: str = "deployed"
    manual_edit_carry_forward: bool = True


def _required(value: str | None, name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{name} is required")
    return cleaned


def _model_name(value: str) -> str:
    cleaned = _required(value, "model_name")
    if not _MODEL_NAME.fullmatch(cleaned):
        raise ValueError(
            "model_name must start with a letter and contain only letters, numbers, and underscores"
        )
    return cleaned


def _package_name(value: str) -> str:
    cleaned = _required(value, "package_name")
    if not _PYTHON_IDENTIFIER.fullmatch(cleaned) or keyword.iskeyword(cleaned):
        raise ValueError("package_name must be a valid Python identifier")
    return cleaned


def _database_mode(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("database_mode must be 'local' or 'remote'")
    cleaned = value.strip().lower()
    if cleaned not in {"local", "remote"}:
        raise ValueError("database_mode must be 'local' or 'remote'")
    return cleaned


def _runtime_module(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("runtime_module must be a dotted Python module name or an empty string")
    cleaned = value.strip()
    if not cleaned:
        return None
    if not _DOTTED_MODULE.fullmatch(cleaned):
        raise ValueError("runtime_module must be a dotted Python module name")
    return cleaned


def _expected_remote_database(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("expected_remote_database must be a string")
    return value.strip()


def _manual_edit_source_selector(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("source_selector must be 'deployed' or 'latest'")
    cleaned = value.strip().lower()
    if cleaned not in {"deployed", "latest"}:
        raise ValueError("source_selector must be 'deployed' or 'latest'")
    return cleaned


def _manual_edit_carry_forward(value: object) -> bool:
    if not isinstance(value, bool):
        raise TypeError("carry_forward must be true or false")
    return value


def resolve_scaffold_options(options: ScaffoldOptions) -> ResolvedScaffoldOptions:
    model_name = _model_name(options.model_name)
    package_name = _package_name(
        options.package_name or re.sub(r"_+", "_", model_name.lower()).strip("_")
    )
    target_name = _required(options.target_name, "target_name")
    model_label = _required(
        options.model_label or model_name.replace("_", " ").title(), "model_label"
    )
    model_type = _required(options.model_type, "model_type")
    deployment_slot = _required(
        options.deployment_slot or f"{model_name}_UAT",
        "deployment_slot",
    )
    database_mode = _database_mode(options.database_mode)
    runtime_module = _runtime_module(options.runtime_module)
    expected_remote_database = _expected_remote_database(options.expected_remote_database)
    manual_edit_source_selector = _manual_edit_source_selector(options.manual_edit_source_selector)
    manual_edit_carry_forward = _manual_edit_carry_forward(options.manual_edit_carry_forward)
    if database_mode == "remote" and not expected_remote_database:
        raise ValueError("expected_remote_database is required when database_mode='remote'")

    return ResolvedScaffoldOptions(
        model_name=model_name,
        target_name=target_name,
        model_label=model_label,
        model_type=model_type,
        deployment_slot=deployment_slot,
        package_name=package_name,
        database_mode=database_mode,
        runtime_module=runtime_module,
        expected_remote_database=expected_remote_database,
        manual_edit_source_selector=manual_edit_source_selector,
        manual_edit_carry_forward=manual_edit_carry_forward,
        root=Path(options.root).resolve(),
        force=options.force,
    )


def load_scaffold_config(path: str | Path) -> ScaffoldConfig:
    """Load strict, non-secret notebook connection defaults from TOML."""
    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise ValueError(f"scaffold config does not exist: {config_path}")
    try:
        with config_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"scaffold config could not be read: {config_path}: {exc}") from exc
    supported_sections = {_CONFIG_SECTION, _MANUAL_EDIT_CONFIG_SECTION}
    unexpected_sections = sorted(set(payload) - supported_sections)
    if unexpected_sections:
        raise ValueError(
            "scaffold config has unsupported top-level sections: " + ", ".join(unexpected_sections)
        )
    raw = payload.get(_CONFIG_SECTION, {})
    if not isinstance(raw, dict):
        raise TypeError(f"[{_CONFIG_SECTION}] must be a TOML table")
    unexpected_keys = sorted(set(raw) - _CONFIG_KEYS)
    if unexpected_keys:
        raise ValueError(f"[{_CONFIG_SECTION}] has unsupported keys: " + ", ".join(unexpected_keys))
    manual_raw = payload.get(_MANUAL_EDIT_CONFIG_SECTION, {})
    if not isinstance(manual_raw, dict):
        raise TypeError(f"[{_MANUAL_EDIT_CONFIG_SECTION}] must be a TOML table")
    unexpected_manual_keys = sorted(set(manual_raw) - {"source_selector", "carry_forward"})
    if unexpected_manual_keys:
        raise ValueError(
            f"[{_MANUAL_EDIT_CONFIG_SECTION}] has unsupported keys: "
            + ", ".join(unexpected_manual_keys)
        )
    return ScaffoldConfig(
        database_mode=_database_mode(raw.get("database_mode", "local")),
        runtime_module=_runtime_module(raw.get("runtime_module")),
        expected_remote_database=_expected_remote_database(raw.get("expected_remote_database", "")),
        manual_edit_source_selector=_manual_edit_source_selector(
            manual_raw.get("source_selector", "deployed")
        ),
        manual_edit_carry_forward=_manual_edit_carry_forward(manual_raw.get("carry_forward", True)),
    )
