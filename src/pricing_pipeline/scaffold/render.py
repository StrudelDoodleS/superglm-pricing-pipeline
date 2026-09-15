"""Render installed notebook and Python templates with validated model options.

Check template names and tokens, substitute Python literals, and return
notebook JSON or Python source. ``service`` chooses where to write it.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from pricing_pipeline.resources import scaffold_notebook_root, scaffold_root
from pricing_pipeline.scaffold.config import ResolvedScaffoldOptions

NOTEBOOK_NAMES = (
    "01_data_ingestion.ipynb",
    "02_model_exploration.ipynb",
    "03_model_training.ipynb",
    "04_model_editor.ipynb",
    "05_manual_adjustment.ipynb",
    "06_model_deployment.ipynb",
    "07_model_monitoring.ipynb",
)

_TEMPLATE_TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*__")


def _python_literal(value: object) -> str:
    """Encode a whole Python value, including quotes or None, for a literal token."""

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
    """Replace known tokens recursively in notebook JSON strings without executing code."""

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


def _template_replacements(options: ResolvedScaffoldOptions) -> dict[str, str]:
    """Encode string contents and complete Python literals for both output types."""

    feature = "feature_1" if options.target_name != "feature_1" else "feature_2"
    primary_key = "row_id" if options.target_name != "row_id" else "record_id"
    string_values = {
        "__PACKAGE_NAME__": options.package_name,
        "__MODEL_NAME__": options.model_name,
        "__MODEL_LABEL__": options.model_label,
        "__TARGET_NAME__": options.target_name,
        "__MODEL_TYPE__": options.model_type,
        "__DEPLOYMENT_SLOT__": options.deployment_slot,
        "__FEATURE_NAME__": feature,
        "__PRIMARY_KEY__": primary_key,
        "__DATASET_NAME__": f"{options.package_name}_model_frame",
        "__MONITORING_DATASET_NAME__": f"{options.package_name}_monitoring",
    }
    replacements = {token: json.dumps(value)[1:-1] for token, value in string_values.items()}
    replacements.update(
        {
            "__MODEL_LABEL_MARKDOWN__": options.model_label,
            "__DATABASE_MODE_LITERAL__": _python_literal(options.database_mode),
            "__RUNTIME_MODULE_LITERAL__": _python_literal(options.runtime_module),
            "__EXPECTED_REMOTE_DATABASE_LITERAL__": _python_literal(
                options.expected_remote_database
            ),
            "__MANUAL_SOURCE_SELECTOR_LITERAL__": _python_literal(
                options.manual_edit_source_selector
            ),
            "__MANUAL_CARRY_FORWARD_LITERAL__": _python_literal(options.manual_edit_carry_forward),
        }
    )
    return replacements


def render_notebooks(options: ResolvedScaffoldOptions) -> dict[str, str]:
    """Map resolved options to template tokens and return notebook JSON by filename.

    For example, ``options.runtime_module`` becomes ``__RUNTIME_MODULE_LITERAL__``,
    which each template places after ``RUNTIME_MODULE =``. String tokens replace
    text already inside quotes; ``*_LITERAL__`` tokens insert the whole Python
    value. ``MODEL_LABEL_MARKDOWN`` supplies the notebook title.

    Templates live in ``resources/scaffold/notebooks``. The service writes this
    function's result into ``pricing_models/<package_name>``.
    """

    replacements = _template_replacements(options)

    rendered: dict[str, str] = {}
    for filename, template in _resource_templates().items():
        unknown = _tokens(template) - replacements.keys()
        if unknown:
            raise RuntimeError(
                "installed scaffold notebook contains unknown template tokens: "
                + ", ".join(sorted(unknown))
            )
        notebook = _render(template, replacements)
        # Validate before substitution: an analyst value may legitimately look like a token.
        rendered[filename] = json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"
    return rendered


def render_monitoring_module(options: ResolvedScaffoldOptions) -> str:
    """Render the editable monitoring script without interpreting analyst values."""

    template = scaffold_root().joinpath("monitoring.py.template").read_text(encoding="utf-8")
    replacements = _template_replacements(options)
    unknown = _tokens(template) - replacements.keys()
    if unknown:
        raise RuntimeError(
            "installed scaffold monitoring module contains unknown template tokens: "
            + ", ".join(sorted(unknown))
        )
    return _TEMPLATE_TOKEN.sub(lambda match: replacements[match.group()], template)
