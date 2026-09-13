"""Describe analyst-supplied validation splitters for audit records.

``Splitter`` defines the required ``split`` interface. ``splitter_config``
records the class and constructor settings; the fitting workflow separately
materializes the actual train/test positions.
"""

import inspect
import json
from collections.abc import Iterable, Mapping
from typing import Any, Protocol

import numpy as np
import pandas as pd

from pricing_pipeline.models.config import ValidationSplitConfig


class Splitter(Protocol):
    """The split(X, y, groups) interface accepted for analyst-defined validation."""

    def split(
        self, X: pd.DataFrame, y: pd.Series | None = None, groups: pd.Series | None = None
    ) -> Iterable[tuple[Any, Any]]: ...


def splitter_config(splitter: Splitter, *, groups_column: str | None) -> ValidationSplitConfig:
    """Snapshot splitter settings; exact row membership is saved separately."""
    if not callable(getattr(splitter, "split", None)):
        raise TypeError("validation must be a ValidationSplitConfig or a splitter with .split()")
    get_params = getattr(splitter, "get_params", None)
    if callable(get_params):
        params = get_params()
    else:
        params = {}
        for name, parameter in inspect.signature(type(splitter).__init__).parameters.items():
            if name == "self" or parameter.kind in (
                parameter.VAR_POSITIONAL,
                parameter.VAR_KEYWORD,
            ):
                continue
            if not hasattr(splitter, name):
                raise ValueError(
                    f"splitter parameter {name!r} must be an attribute or supplied by get_params()"
                )
            params[name] = getattr(splitter, name)
    if not isinstance(params, Mapping):
        raise TypeError("splitter get_params() must return a JSON-compatible mapping")
    try:
        params = json.loads(json.dumps(dict(params), default=_json_parameter, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "splitter parameters must be JSON-compatible; use an integer random_state seed"
        ) from exc
    return ValidationSplitConfig(
        method="custom",
        n_splits=None,
        random_state=None,
        shuffle=False,
        materialize=True,
        splitter_class=f"{type(splitter).__module__}.{type(splitter).__qualname__}",
        splitter_params=params,
        groups_column=groups_column,
    )


def _json_parameter(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"unsupported splitter parameter type: {type(value).__name__}")
