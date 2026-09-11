"""Small, serializable dataframe transforms declared alongside a model spec."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd


def _name(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty name without surrounding whitespace")
    return value


@dataclass(frozen=True)
class Log:
    source: str

    def __post_init__(self) -> None:
        _name(self.source, field="source")

    @property
    def expression(self) -> str:
        return f"log({self.source})"

    def to_dict(self) -> dict[str, Any]:
        return {"operation": "log", "source": self.source}


@dataclass(frozen=True)
class Log1p:
    source: str

    def __post_init__(self) -> None:
        _name(self.source, field="source")

    @property
    def expression(self) -> str:
        return f"log1p({self.source})"

    def to_dict(self) -> dict[str, Any]:
        return {"operation": "log1p", "source": self.source}


@dataclass(frozen=True)
class Clip:
    source: str
    lower: float | None = None
    upper: float | None = None

    def __post_init__(self) -> None:
        _name(self.source, field="source")
        if self.lower is None and self.upper is None:
            raise ValueError("clip requires at least one bound")
        for field in ("lower", "upper"):
            value = getattr(self, field)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
                    raise ValueError(f"clip {field} bound must be a finite number")
                object.__setattr__(self, field, float(value))
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("clip lower bound must not exceed upper bound")

    @property
    def expression(self) -> str:
        return f"clip({self.source}, lower={self.lower!r}, upper={self.upper!r})"

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": "clip",
            "source": self.source,
            "lower": self.lower,
            "upper": self.upper,
        }


type Transform = Log | Log1p | Clip


def normalize_transforms(transforms: Mapping[str, Transform] | None) -> Mapping[str, Transform]:
    """Freeze a declaration mapping, preserving the declared output order."""
    if transforms is None:
        return MappingProxyType({})
    if not isinstance(transforms, Mapping):
        raise TypeError("transforms must be a mapping of output names to transforms")
    result = {}
    for output, transform in transforms.items():
        _name(output, field="transform output name")
        if type(transform) not in (Log, Log1p, Clip):
            raise TypeError(f"transform {output!r} must be Log, Log1p, or Clip")
        result[output] = transform
    return MappingProxyType(result)


def transforms_metadata(transforms: Mapping[str, Transform] | None) -> dict[str, dict[str, Any]]:
    """Return JSON-native evidence for each declared output."""
    return {
        name: transform.to_dict() for name, transform in normalize_transforms(transforms).items()
    }


def transforms_from_metadata(
    metadata: Mapping[str, Mapping[str, Any]] | None,
) -> Mapping[str, Transform]:
    """Read only supported declarations, rejecting unknown operations and fields."""
    if metadata is None:
        return normalize_transforms(None)
    if not isinstance(metadata, Mapping):
        raise TypeError("transform metadata must be a mapping")
    result = {}
    classes = {"log": Log, "log1p": Log1p, "clip": Clip}
    for output, payload in metadata.items():
        if not isinstance(payload, Mapping):
            raise TypeError("transform metadata values must be mappings")
        operation = payload.get("operation")
        if not isinstance(operation, str) or operation not in classes:
            raise ValueError(f"unsupported transform operation {operation!r}")
        required = {"operation", "source"}
        allowed = required | ({"lower", "upper"} if operation == "clip" else set())
        if not required <= payload.keys() or not payload.keys() <= allowed:
            raise ValueError(f"invalid metadata fields for transform {output!r}")
        arguments = {key: value for key, value in payload.items() if key != "operation"}
        result[output] = classes[operation](**arguments)
    return normalize_transforms(result)


def _copy_frame(df: pd.DataFrame) -> pd.DataFrame:
    copied = df.copy(deep=True)
    # DataFrame.copy shares axis arrays even with deep=True.
    copied.index = df.index.copy(deep=True)
    copied.columns = df.columns.copy(deep=True)
    # pandas deep copies its arrays but shares Python objects stored in cells.
    for position, dtype in enumerate(df.dtypes):
        if pd.api.types.is_object_dtype(dtype):
            copied.isetitem(position, deepcopy(df.iloc[:, position].to_numpy()))
    return copied


def apply_transforms(df: pd.DataFrame, transforms: Mapping[str, Transform] | None) -> pd.DataFrame:
    """Copy a frame and append transforms of its original columns.

    Sources must be original columns. Chained transforms and overwriting existing
    columns are rejected so declaration order never changes a calculation.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if not df.columns.is_unique:
        raise ValueError("dataframe column names must be unique")
    declarations = normalize_transforms(transforms)
    result = _copy_frame(df)
    for output, transform in declarations.items():
        if output in df.columns:
            raise ValueError(f"transform output {output!r} already exists in the dataframe")
        if transform.source not in df.columns:
            raise ValueError(
                f"transform source {transform.source!r} must be an original dataframe column; "
                "transform dependencies are not supported"
            )
        values = df[transform.source]
        if (
            not pd.api.types.is_numeric_dtype(values.dtype)
            or pd.api.types.is_bool_dtype(values.dtype)
            or pd.api.types.is_complex_dtype(values.dtype)
        ):
            raise TypeError(f"transform source {transform.source!r} must contain real numeric data")
        numeric = values.to_numpy(dtype=float, na_value=np.nan)
        if not np.isfinite(numeric).all():
            raise ValueError(f"transform source {transform.source!r} must contain finite values")
        if isinstance(transform, Log):
            if (numeric <= 0).any():
                raise ValueError(f"log source {transform.source!r} must be greater than zero")
            result[output] = np.log(numeric)
        elif isinstance(transform, Log1p):
            if (numeric <= -1).any():
                raise ValueError(f"log1p source {transform.source!r} must be greater than -1")
            result[output] = np.log1p(numeric)
        else:
            if pd.api.types.is_integer_dtype(values.dtype) and (
                (
                    transform.lower is not None
                    and not transform.lower.is_integer()
                    and (values < transform.lower).any()
                )
                or (
                    transform.upper is not None
                    and not transform.upper.is_integer()
                    and (values > transform.upper).any()
                )
            ):
                dtype = (
                    "Float64"
                    if isinstance(values.dtype, pd.api.extensions.ExtensionDtype)
                    else "float64"
                )
                values = values.astype(dtype)
            result[output] = values.clip(lower=transform.lower, upper=transform.upper)
    return result


__all__ = [
    "Clip",
    "Log",
    "Log1p",
    "Transform",
    "apply_transforms",
    "normalize_transforms",
    "transforms_from_metadata",
    "transforms_metadata",
]
