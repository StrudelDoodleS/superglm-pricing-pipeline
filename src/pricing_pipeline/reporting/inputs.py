"""Input contracts and validation for aggregate reporting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

ProblemType = Literal["frequency", "severity", "burn_cost"]
ColumnOrValues = str | Sequence[float] | np.ndarray | pd.Series
ComparisonUnit = str | Sequence[Any] | np.ndarray | pd.Series

MAX_MAIN_EFFECT_GRID_POINTS = 512
MAX_SURFACE_AXIS_POINTS = 160

_PROBLEM_DEFAULT_POWER: Mapping[str, float] = {
    "frequency": 1.0,
    "severity": 2.0,
    "burn_cost": 1.5,
}


class UnderwriterReportError(RuntimeError):
    """Raised when a trustworthy report cannot be produced."""


@dataclass(frozen=True)
class UnderwriterReportOptions:
    """Display and aggregation choices for one report."""

    title: str = "Pricing model review"
    problem_type: ProblemType = "burn_cost"
    tweedie_power: float | None = None
    top_k: int = 12
    double_lift_bins: int = 10
    curve_bins: int = 100
    distribution_bins: int = 200
    movement_bins: int = 10
    relativity_points: int = 200
    interaction_points: int = 80
    comparison_bootstrap_replicates: int = 200
    comparison_bootstrap_seed: int = 1729
    minimum_cell_size: int = 20

    def __post_init__(self) -> None:
        title = self.title.strip()
        if not title:
            raise ValueError("title must be non-empty")
        if self.problem_type not in _PROBLEM_DEFAULT_POWER:
            raise ValueError("problem_type must be frequency, severity, or burn_cost")
        power = self.resolved_tweedie_power
        if self.problem_type == "frequency" and power != 1.0:
            raise ValueError("frequency reports use Poisson deviance (tweedie_power=1)")
        if self.problem_type == "severity" and power != 2.0:
            raise ValueError("severity reports use Gamma deviance (tweedie_power=2)")
        if self.problem_type == "burn_cost" and not 1.0 < power < 2.0:
            raise ValueError("burn_cost tweedie_power must be strictly between 1 and 2")
        for name in (
            "top_k",
            "double_lift_bins",
            "curve_bins",
            "distribution_bins",
            "movement_bins",
            "relativity_points",
            "interaction_points",
        ):
            value = getattr(self, name)
            minimum = 2 if name != "top_k" else 1
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                raise ValueError(f"{name} must be an integer of at least {minimum}")
            if name == "relativity_points" and value > MAX_MAIN_EFFECT_GRID_POINTS:
                raise ValueError(f"relativity_points must be at most {MAX_MAIN_EFFECT_GRID_POINTS}")
            if name == "interaction_points" and value > MAX_SURFACE_AXIS_POINTS:
                raise ValueError(f"interaction_points must be at most {MAX_SURFACE_AXIS_POINTS}")
        replicates = self.comparison_bootstrap_replicates
        if (
            not isinstance(replicates, int)
            or isinstance(replicates, bool)
            or (replicates != 0 and replicates < 100)
        ):
            raise ValueError(
                "comparison_bootstrap_replicates must be zero or an integer of at least 100"
            )
        seed = self.comparison_bootstrap_seed
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            raise ValueError("comparison_bootstrap_seed must be a non-negative integer")
        if (
            not isinstance(self.minimum_cell_size, int)
            or isinstance(self.minimum_cell_size, bool)
            or self.minimum_cell_size < 2
        ):
            raise ValueError("minimum_cell_size must be an integer of at least 2")

    @property
    def resolved_tweedie_power(self) -> float:
        """Return the explicit power or the problem-type default."""
        if self.tweedie_power is None:
            return _PROBLEM_DEFAULT_POWER[self.problem_type]
        return float(self.tweedie_power)


@dataclass(frozen=True)
class UnderwriterReportResult:
    """Useful aggregate evidence returned alongside the HTML file."""

    output_path: Path
    metrics: pd.DataFrame
    importance: Mapping[str, pd.DataFrame]
    rows_used: int
    zero_weight_rows_ignored: int


@dataclass(frozen=True)
class ValidatedReportInputs:
    frame: pd.DataFrame
    actual: np.ndarray
    predictions: Mapping[str, np.ndarray]
    weight: np.ndarray
    features: tuple[str, ...]
    comparison_unit_codes: np.ndarray
    comparison_units: int
    zero_weight_rows_ignored: int
    offset: np.ndarray | None


def _column_or_vector(
    frame: pd.DataFrame,
    value: ColumnOrValues,
    name: str,
) -> np.ndarray:
    if isinstance(value, str):
        if value not in frame.columns:
            raise KeyError(f"{name} column is missing: {value!r}")
        value = frame[value]
    out = np.asarray(value, dtype=float)
    if out.ndim != 1 or len(out) != len(frame):
        raise ValueError(f"{name} must be one-dimensional and match the frame")
    if not np.isfinite(out).all():
        raise ValueError(f"{name} must contain only finite values")
    return out


def normalize_report_inputs(
    frame: pd.DataFrame,
    *,
    actual: ColumnOrValues,
    predictions: Mapping[str, ColumnOrValues],
    sample_weight: ColumnOrValues,
    features: Sequence[str],
    offset: ColumnOrValues | None,
    comparison_unit: ComparisonUnit | None,
    options: UnderwriterReportOptions,
) -> ValidatedReportInputs:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("frame must be a non-empty pandas DataFrame")
    feature_names = tuple(str(feature) for feature in features)
    if not feature_names or any(not name.strip() for name in feature_names):
        raise ValueError("features must contain at least one non-empty column name")
    if len(set(feature_names)) != len(feature_names):
        raise ValueError("features must not contain duplicates")
    missing_features = set(feature_names) - set(frame.columns)
    if missing_features:
        raise KeyError("report features are missing: " + ", ".join(sorted(missing_features)))
    if not isinstance(predictions, Mapping) or not predictions:
        raise ValueError("predictions must contain at least one named model")

    y = _column_or_vector(frame, actual, "actual")
    weight = _column_or_vector(frame, sample_weight, "sample_weight")
    if np.any(weight < 0) or not np.any(weight > 0):
        raise ValueError("sample_weight must be non-negative with at least one positive value")
    if np.any(y < 0):
        raise ValueError("actual must be non-negative")
    positive = weight > 0
    resolved_offset = None if offset is None else _column_or_vector(frame, offset, "offset")
    if options.resolved_tweedie_power >= 2.0 and np.any(y[positive] <= 0):
        raise ValueError("severity actuals must be strictly positive for Gamma deviance")

    resolved_predictions: dict[str, np.ndarray] = {}
    for raw_name, values in predictions.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("prediction model names must be non-empty")
        if name.lower() in {"__all__", "actual", "none"}:
            raise ValueError(f"prediction model name is reserved by report controls: {name!r}")
        if name in resolved_predictions:
            raise ValueError(f"duplicate prediction model name: {name!r}")
        prediction = _column_or_vector(frame, values, f"prediction {name!r}")
        if np.any(prediction[positive] <= 0):
            raise ValueError(f"prediction {name!r} must contain strictly positive values")
        resolved_predictions[name] = prediction

    ignored = int((~positive).sum())
    if comparison_unit is None:
        unit_values = np.arange(len(frame), dtype=np.int64)[positive]
    else:
        if isinstance(comparison_unit, str):
            if comparison_unit not in frame.columns:
                raise KeyError(f"comparison_unit column is missing: {comparison_unit!r}")
            if comparison_unit in feature_names:
                raise ValueError(
                    "comparison_unit identifier cannot also be a report feature: "
                    f"{comparison_unit!r}"
                )
            comparison_unit = frame[comparison_unit]
        raw_units = np.asarray(comparison_unit, dtype=object)
        if raw_units.ndim != 1 or len(raw_units) != len(frame):
            raise ValueError("comparison_unit must be one-dimensional and match the frame")
        unit_values = raw_units[positive]
        if pd.isna(unit_values).any():
            raise ValueError("comparison_unit must not contain missing values on positive rows")
    try:
        unit_codes, unique_units = pd.factorize(unit_values, sort=False)
    except TypeError as exc:
        raise ValueError("comparison_unit values must be hashable") from exc
    if len(unique_units) < options.minimum_cell_size:
        raise ValueError(
            "aggregate reporting requires at least "
            f"{options.minimum_cell_size} distinct comparison units; got {len(unique_units)}"
        )
    return ValidatedReportInputs(
        frame=frame.loc[positive].reset_index(drop=True),
        actual=y[positive],
        predictions={name: values[positive] for name, values in resolved_predictions.items()},
        weight=weight[positive],
        features=feature_names,
        comparison_unit_codes=np.asarray(unit_codes, dtype=np.intp),
        comparison_units=len(unique_units),
        zero_weight_rows_ignored=ignored,
        offset=None if resolved_offset is None else resolved_offset[positive],
    )
