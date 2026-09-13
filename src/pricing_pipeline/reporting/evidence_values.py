"""Validate scalar values, reporting context and category identities in model evidence.

These checks are shared by main-feature and interaction normalization. They
copy values or reject invalid inputs without collecting or rendering reports."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from numbers import Integral, Real

import numpy as np
import pandas as pd

from pricing_pipeline.reporting.evidence_types import (
    _INTERACTION_PLOT_KINDS,
    _PROBLEM_POWERS,
    _SEMANTICS,
    EvidenceFact,
    EvidenceSemantic,
    InteractionPlotKind,
    ReportContext,
)


def _context_category_labels(feature: str, context: ReportContext) -> pd.Series:
    labels: list[str] = []
    identities: dict[str, tuple[object, ...]] = {}
    for raw_value in context.frame[feature].tolist():
        label = _plain_text(str(raw_value), f"context feature {feature!r} category")
        identity = _raw_category_identity(raw_value)
        prior_identity = identities.get(label)
        if prior_identity is not None and prior_identity != identity:
            raise ValueError(
                f"context feature {feature!r}: distinct categories have an ambiguous "
                "text representation"
            )
        identities[label] = identity
        labels.append(label)
    return pd.Series(labels, index=context.frame.index, dtype="object")


def _raw_category_identity(value: object) -> tuple[object, ...]:
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):  # fmt: skip
        missing = False
    if isinstance(missing, (bool, np.bool_)) and missing:
        return ("missing",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, Integral):
        return ("integer", int(value))
    if isinstance(value, Real):
        return ("real", float(value))
    if isinstance(value, str):
        return ("text", value)
    return (type(value).__qualname__, repr(value))


def _normalize_facts(facts: Sequence[EvidenceFact]) -> tuple[EvidenceFact, ...]:
    normalized: list[EvidenceFact] = []
    for fact in facts:
        if not isinstance(fact, EvidenceFact):
            raise TypeError("facts must contain EvidenceFact values")
        value = fact.value
        if isinstance(value, str):
            value = _plain_text(value, "fact.value")
        elif value is not None and not isinstance(value, (bool, Integral, Real)):
            raise TypeError("fact.value must be a scalar display value")
        elif (
            isinstance(value, Real)
            and not isinstance(value, bool)
            and not math.isfinite(float(value))
        ):
            raise ValueError("fact.value must be finite")
        normalized.append(EvidenceFact(_plain_text(fact.label, "fact.label"), value))
    return tuple(normalized)


def _normalize_warnings(warnings: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(warnings, tuple):
        raise TypeError("warnings must be a tuple of plain text values")
    return tuple(_plain_text(warning, "warnings") for warning in warnings)


def _validate_context(context: ReportContext) -> None:
    if not isinstance(context, ReportContext):
        raise TypeError("context must be ReportContext")
    if not isinstance(context.frame, pd.DataFrame):
        raise TypeError("context.frame must be a pandas DataFrame")
    rows = len(context.frame)
    if rows == 0:
        raise ValueError("context.frame must not be empty")
    actual = _numeric_vector(context.actual, "context.actual")
    weight = _numeric_vector(context.weight, "context.weight")
    offset = None if context.offset is None else _numeric_vector(context.offset, "context.offset")
    codes = np.asarray(context.comparison_unit_codes)
    if len(actual) != rows or len(weight) != rows or (offset is not None and len(offset) != rows):
        raise ValueError("context vectors must match context.frame length")
    if (weight <= 0.0).any():
        raise ValueError("context.weight must be positive")
    if codes.ndim != 1 or len(codes) != rows or not np.issubdtype(codes.dtype, np.integer):
        raise ValueError("context.comparison_unit_codes must be one-dimensional integer codes")
    if not isinstance(context.predictions, Mapping) or not context.predictions:
        raise ValueError("context.predictions must be a non-empty mapping")
    for model_name, prediction in context.predictions.items():
        _plain_text(model_name, "context prediction name")
        if len(_numeric_vector(prediction, "context.prediction")) != rows:
            raise ValueError("context predictions must match context.frame length")
    if not isinstance(context.features, tuple) or not context.features:
        raise ValueError("context.features must be a non-empty tuple")
    for feature in context.features:
        feature = _plain_text(feature, "context feature")
        if feature not in context.frame.columns:
            raise ValueError(f"context feature {feature!r} is missing from context.frame")
    if len(set(context.features)) != len(context.features):
        raise ValueError("context.features must not contain duplicates")
    if not isinstance(context.comparison_units, int) or isinstance(context.comparison_units, bool):
        raise TypeError("context.comparison_units must be an integer")
    if context.comparison_units <= 0:
        raise ValueError("context.comparison_units must be positive")
    if not isinstance(context.minimum_cell_size, int) or isinstance(
        context.minimum_cell_size, bool
    ):
        raise TypeError("context.minimum_cell_size must be an integer")
    if context.minimum_cell_size <= 0:
        raise ValueError("context.minimum_cell_size must be positive")
    if context.problem_type not in {"frequency", "severity", "burn_cost"}:
        raise ValueError("context.problem_type is invalid")
    power = _finite_number(context.deviance_power, "context.deviance_power")
    if context.problem_type in _PROBLEM_POWERS and power != _PROBLEM_POWERS[context.problem_type]:
        raise ValueError("context.deviance_power is incompatible with problem_type")
    if context.problem_type == "burn_cost" and not 1.0 < power < 2.0:
        raise ValueError("burn_cost context.deviance_power must be between 1 and 2")


def _validate_model_name(model_name: str, context: ReportContext) -> None:
    normalized_name = _plain_text(model_name, "model_name")
    if model_name != normalized_name or model_name not in context.predictions:
        raise KeyError(f"unknown model name: {model_name!r}")


def _semantic(value: object, name: str) -> EvidenceSemantic:
    if value not in _SEMANTICS:
        raise ValueError(f"{name} is invalid")
    return value


def _plot_kind(value: object) -> InteractionPlotKind:
    if value not in _INTERACTION_PLOT_KINDS:
        raise ValueError("interaction.plot_kind is invalid")
    return value


def _plain_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    value = value.strip()
    if not value or "<" in value or ">" in value:
        raise ValueError(f"{name} must be plain non-empty text without HTML tags")
    return value


def _data_frame(value: object, name: str) -> pd.DataFrame:
    if not isinstance(value, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")
    return value.copy(deep=True)


def _array(value: object, name: str) -> np.ndarray:
    result = np.asarray(value)
    if result.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    return result.copy()


def _numeric_vector(value: object, name: str) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must be numeric") from error
    if result.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must contain only finite values")
    return result.copy()


def _numeric_column(value: pd.Series, name: str) -> np.ndarray:
    if pd.api.types.is_bool_dtype(value) or not pd.api.types.is_numeric_dtype(value):
        raise TypeError(f"{name} must be numeric")
    result = value.to_numpy(dtype=float, copy=True)
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must contain only finite values")
    return result


def _text_column(value: pd.Series, name: str) -> pd.Series:
    normalized = [_plain_text(item, name) for item in value.tolist()]
    return pd.Series(normalized, index=value.index, dtype="object")


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _optional_finite_number(value: object, name: str) -> float | None:
    return None if value is None else _finite_number(value, name)
