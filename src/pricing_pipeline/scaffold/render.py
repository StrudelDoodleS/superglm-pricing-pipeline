from __future__ import annotations

import json
import re
from collections.abc import Mapping

from pricing_pipeline.resources import scaffold_notebook_root

NOTEBOOK_NAMES = (
    "01_data_ingestion.ipynb",
    "02_model_exploration.ipynb",
    "03_model_training.ipynb",
    "04_model_editor.ipynb",
    "05_manual_adjustment.ipynb",
    "06_model_deployment.ipynb",
)

_TEMPLATE_TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*__")


def _python_literal(value: object) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return repr(value)
    return json.dumps(value, ensure_ascii=False)


def _tokens(value: object) -> set[str]:
    if isinstance(value, str):
        return set(_TEMPLATE_TOKEN.findall(value))
    if isinstance(value, list):
        return set().union(*(_tokens(item) for item in value), set())
    if isinstance(value, dict):
        return set().union(*(_tokens(item) for item in value.values()), set())
    return set()


def _render(value: object, replacements: Mapping[str, str]) -> object:
    if isinstance(value, str):
        return _TEMPLATE_TOKEN.sub(lambda match: replacements[match.group()], value)
    if isinstance(value, list):
        return [_render(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _render(item, replacements) for key, item in value.items()}
    return value


def _resource_templates() -> dict[str, dict[str, object]]:
    root = scaffold_notebook_root()
    names = tuple(sorted(item.name for item in root.iterdir() if item.is_file()))
    if names != tuple(sorted(NOTEBOOK_NAMES)):
        raise RuntimeError("installed scaffold notebook resource inventory is invalid")
    return {
        name: json.loads(root.joinpath(name).read_text(encoding="utf-8")) for name in NOTEBOOK_NAMES
    }


def render_notebooks(
    *,
    package_name: str,
    model_name: str,
    model_label: str,
    target_name: str,
    model_type: str,
    deployment_slot: str,
    database_mode: str,
    runtime_module: str | None,
    expected_remote_database: str,
    manual_edit_source_selector: str,
    manual_edit_carry_forward: bool,
) -> dict[str, str]:
    feature = "feature_1" if target_name != "feature_1" else "feature_2"
    primary_key = "row_id" if target_name != "row_id" else "record_id"
    string_values = {
        "__PACKAGE_NAME__": package_name,
        "__MODEL_NAME__": model_name,
        "__MODEL_LABEL__": model_label,
        "__TARGET_NAME__": target_name,
        "__MODEL_TYPE__": model_type,
        "__DEPLOYMENT_SLOT__": deployment_slot,
        "__FEATURE_NAME__": feature,
        "__PRIMARY_KEY__": primary_key,
        "__DATASET_NAME__": f"{package_name}_model_frame",
    }
    replacements = {
        token: json.dumps(value, ensure_ascii=False)[1:-1] for token, value in string_values.items()
    }
    replacements.update(
        {
            "__MODEL_LABEL_MARKDOWN__": model_label,
            "__DATABASE_MODE_LITERAL__": _python_literal(database_mode),
            "__RUNTIME_MODULE_LITERAL__": _python_literal(runtime_module),
            "__EXPECTED_REMOTE_DATABASE_LITERAL__": _python_literal(expected_remote_database),
            "__MANUAL_SOURCE_SELECTOR_LITERAL__": _python_literal(manual_edit_source_selector),
            "__MANUAL_CARRY_FORWARD_LITERAL__": _python_literal(manual_edit_carry_forward),
        }
    )

    rendered: dict[str, str] = {}
    for filename, template in _resource_templates().items():
        unknown = _tokens(template) - replacements.keys()
        if unknown:
            raise RuntimeError(
                "installed scaffold notebook contains unknown template tokens: "
                + ", ".join(sorted(unknown))
            )
        notebook = _render(template, replacements)
        unresolved = _tokens(notebook)
        if unresolved:
            raise RuntimeError(
                "installed scaffold notebook contains unresolved template tokens: "
                + ", ".join(sorted(unresolved))
            )
        rendered[filename] = json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"
    return rendered
