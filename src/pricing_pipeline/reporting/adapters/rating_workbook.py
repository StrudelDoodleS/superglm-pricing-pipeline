"""Evidence adapter for exported SuperGLM rating-table workbooks.

This module intentionally has no dependency on the SuperGLM Python package.
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pricing_pipeline.publishing.spline_segments import validate_spline_rows
from pricing_pipeline.reporting.evidence import (
    FeatureImportanceEvidence,
    MainEffectEvidence,
    ModelEvidence,
    ReportContext,
    SuppressionMetadata,
)
from pricing_pipeline.reporting.inputs import UnderwriterReportError

_RATING_SHEET = "Rating Tables"
_TERM_ROW = 4
_HEADER_ROW = 6
_DATA_START_ROW = 7
_SOURCE = "rating workbook"
_LEVEL_HEADERS = frozenset({"level", "levels", "category", "categories", "value", "values"})
_NUMBER_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_INTERVAL_RE = re.compile(rf"^\s*\[\s*({_NUMBER_PATTERN})\s*,\s*({_NUMBER_PATTERN})\s*\)\s*$")


class RatingWorkbookAdapter:
    """Translate one exported rating workbook into neutral model evidence."""

    def collect(
        self,
        *,
        model_name: str,
        source: object,
        context: ReportContext,
    ) -> ModelEvidence:
        del model_name
        if not isinstance(source, (str, os.PathLike)):
            raise TypeError("rating workbook source must be path-like")
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"rating workbook does not exist: {path}")
        allowed = set(context.features)
        blocks = {
            feature: values
            for feature, values in _workbook_blocks(path).items()
            if feature in allowed
        }
        main_effects = {
            feature: _main_effect(feature, block, context) for feature, block in blocks.items()
        }
        return ModelEvidence(
            source=_SOURCE,
            importance=FeatureImportanceEvidence(
                table=_workbook_importance(blocks, context),
                method="export_log_relativity_variance",
                source=_SOURCE,
            ),
            main_effects=main_effects,
        )


def _workbook_blocks(path: Path) -> dict[str, dict[str, Any]]:
    try:
        raw = pd.read_excel(path, sheet_name=_RATING_SHEET, header=None, engine="openpyxl")
    except Exception as exc:
        raise UnderwriterReportError(f"could not read rating workbook: {path}") from exc

    blocks: dict[str, dict[str, Any]] = {}
    normalized_names: set[str] = set()
    for column in range(max(raw.shape[1] - 2, 0)):
        title = raw.iat[_TERM_ROW, column] if _TERM_ROW < raw.shape[0] else None
        headers = (
            [raw.iat[_HEADER_ROW, column + offset] for offset in range(3)]
            if _HEADER_ROW < raw.shape[0]
            else [None, None, None]
        )
        if pd.isna(title) or any(pd.isna(value) for value in headers):
            continue
        normalized = [str(value).strip().lower() for value in headers]
        if "relativity" not in normalized[1] or "weight" not in normalized[2]:
            continue
        name = str(title).strip()
        normalized_name = _normalize_label(name)
        if normalized[0] not in _LEVEL_HEADERS and _normalize_label(headers[0]) != normalized_name:
            raise UnderwriterReportError(
                f"rating workbook term {name!r} has an ambiguous level header"
            )
        if normalized_name in normalized_names:
            raise UnderwriterReportError(f"rating workbook contains duplicate term {name!r}")
        normalized_names.add(normalized_name)
        levels: list[str] = []
        relativities: list[float] = []
        weights: list[float] = []
        coefficient_headers = []
        for offset in range(3, min(7, raw.shape[1] - column)):
            if pd.notna(raw.iat[_TERM_ROW, column + offset]):
                break
            coefficient_headers.append(str(raw.iat[_HEADER_ROW, column + offset]).strip().lower())
        is_spline = any(value in {"a", "b", "c", "d"} for value in coefficient_headers)
        has_coefficient_headers = any(value not in {"", "nan"} for value in coefficient_headers)
        if has_coefficient_headers and coefficient_headers != ["a", "b", "c", "d"]:
            raise UnderwriterReportError(
                f"rating workbook term {name!r} has partial spline headers"
            )
        segments = []
        for row in range(_DATA_START_ROW, raw.shape[0]):
            level = raw.iat[row, column]
            relativity = raw.iat[row, column + 1]
            weight = raw.iat[row, column + 2]
            coefficient_values = raw.iloc[row, column + 3 : column + 3 + len(coefficient_headers)]
            has_coefficient_data = coefficient_values.notna().any()
            if has_coefficient_data and not is_spline:
                raise UnderwriterReportError(
                    f"rating workbook term {name!r} has spline coefficients without headers a, b, c, d"
                )
            if (
                is_spline
                and (pd.isna(level) or pd.isna(relativity))
                and (
                    pd.notna(level)
                    or pd.notna(relativity)
                    or pd.notna(weight)
                    or has_coefficient_data
                )
            ):
                raise UnderwriterReportError(
                    f"rating workbook term {name!r} contains an incomplete spline row"
                )
            if pd.isna(level) and pd.isna(relativity):
                if levels:
                    break
                continue
            if pd.isna(level) or pd.isna(relativity):
                break
            try:
                resolved_relativity = float(relativity)
                resolved_weight = 1.0 if pd.isna(weight) else float(weight)
            except (TypeError, ValueError) as exc:
                raise UnderwriterReportError(
                    f"rating workbook term {name!r} contains non-numeric relativity/weight"
                ) from exc
            if not math.isfinite(resolved_relativity) or resolved_relativity <= 0.0:
                raise UnderwriterReportError(
                    f"rating workbook term {name!r} contains an invalid relativity"
                )
            if not math.isfinite(resolved_weight) or resolved_weight < 0.0:
                raise UnderwriterReportError(
                    f"rating workbook term {name!r} contains an invalid weight"
                )
            levels.append(str(level).strip())
            relativities.append(resolved_relativity)
            weights.append(resolved_weight)
            if is_spline:
                segments.append(
                    {
                        "level_code": levels[-1],
                        "multiplier": resolved_relativity,
                        **{
                            f"spline_{key}": raw.iat[row, column + 3 + index]
                            for index, key in enumerate(("a", "b", "c", "d"))
                        },
                    }
                )
        if not levels:
            continue
        if not any(weights):
            weights = [1.0] * len(weights)
        blocks[name] = {
            "labels": levels,
            "relativity": relativities,
            "weight": weights,
        }
        if is_spline:
            try:
                blocks[name]["segments"] = validate_spline_rows(segments)
            except ValueError as exc:
                raise UnderwriterReportError(f"rating workbook term {name!r}: {exc}") from exc
    if not blocks:
        raise UnderwriterReportError(f"no main-effect blocks found on {_RATING_SHEET!r} in {path}")
    return blocks


def _normalize_label(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _main_effect(
    feature: str,
    block: dict[str, Any],
    context: ReportContext,
) -> MainEffectEvidence:
    numeric_values = _numeric_context_values(context.frame[feature])
    if "segments" in block:
        if numeric_values is None:
            raise UnderwriterReportError(
                f"rating workbook spline {feature!r} requires numeric values"
            )
        return _spline_main_effect(feature, block["segments"], numeric_values, context)
    intervals = (
        _continuous_intervals(feature, block["labels"]) if numeric_values is not None else None
    )
    if intervals is None:
        return MainEffectEvidence(
            feature=feature,
            semantic="native_component",
            effect=pd.DataFrame(
                {
                    "label": block["labels"],
                    "value": block["relativity"],
                }
            ),
            source=_SOURCE,
        )

    codes = np.asarray(context.comparison_unit_codes)
    weights = np.asarray(context.weight, dtype=float)
    coordinates = [lower + (upper - lower) / 2.0 for lower, upper in intervals]
    masks = [
        _interval_membership(numeric_values, intervals, index) for index in range(len(intervals))
    ]
    safe = [len(np.unique(codes[mask])) >= context.minimum_cell_size for mask in masks]
    if not all(safe):
        return MainEffectEvidence(
            feature=feature,
            semantic="native_component",
            effect=pd.DataFrame({"x": [], "value": []}, dtype=float),
            source=_SOURCE,
            suppression=SuppressionMetadata(
                status="partial" if any(safe) else "all",
                reason="minimum_support",
                presentation="curve_omitted",
            ),
        )
    exposures = [float(weights[mask].sum()) for mask in masks]
    relativities = [
        float(relativity)
        for (_lower, _upper), relativity in zip(
            intervals,
            block["relativity"],
            strict=True,
        )
    ]
    return MainEffectEvidence(
        feature=feature,
        semantic="native_component",
        effect=pd.DataFrame({"x": coordinates, "value": relativities}),
        source=_SOURCE,
        density=pd.DataFrame({"x": coordinates, "density": exposures}),
    )


def _interval_membership(
    values: np.ndarray,
    intervals: list[tuple[float, float]],
    index: int,
) -> np.ndarray:
    lower, upper = intervals[index]
    if len(intervals) == 1:
        return np.isfinite(values)
    if index == 0:
        return values < upper
    if index == len(intervals) - 1:
        return values >= lower
    return (values >= lower) & (values < upper)


def _numeric_context_values(values: pd.Series) -> np.ndarray | None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric[values.notna()].isna().any():
        return None
    return numeric.to_numpy(dtype=float)


def _continuous_intervals(
    feature: str,
    labels: list[str],
) -> list[tuple[float, float]] | None:
    matches = [_INTERVAL_RE.fullmatch(label) for label in labels]
    if not any(matches):
        return None
    if not all(matches):
        raise UnderwriterReportError(
            f"rating workbook term {feature!r} mixes interval and categorical levels"
        )
    intervals = [(float(match.group(1)), float(match.group(2))) for match in matches if match]
    for index, (lower, upper) in enumerate(intervals):
        if not math.isfinite(lower) or not math.isfinite(upper) or lower >= upper:
            raise UnderwriterReportError(
                f"rating workbook term {feature!r} contains an invalid interval"
            )
        if index and lower != intervals[index - 1][1]:
            raise UnderwriterReportError(
                f"rating workbook term {feature!r} contains non-contiguous intervals"
            )
    return intervals


def _weighted_mean(values: np.ndarray, weight: np.ndarray) -> float:
    return float(np.average(values, weights=weight))


def _spline_log_effect(segments: list[dict[str, Any]], values: np.ndarray) -> np.ndarray:
    result = np.full(values.shape, np.nan, dtype=float)
    for segment in segments:
        lower, upper = segment["spline_lower"], segment["spline_upper"]
        mask = np.isfinite(values)
        if lower is not None:
            mask &= values >= lower
        if upper is not None:
            mask &= values <= upper if segment["spline_upper_inclusive"] else values < upper
        u = 0.0 if lower is None or upper is None else (values[mask] - lower) / (upper - lower)
        a, b, c, d = (segment[f"spline_{key}"] for key in ("a", "b", "c", "d"))
        result[mask] = a + u * (b + u * (c + u * d))
    if np.any(np.isfinite(values) & ~np.isfinite(result)):
        raise UnderwriterReportError(
            "rating workbook spline values fall outside the exported domain"
        )
    return result


def _spline_main_effect(
    feature: str,
    segments: list[dict[str, Any]],
    values: np.ndarray,
    context: ReportContext,
) -> MainEffectEvidence:
    _spline_log_effect(segments, values)
    intervals = [
        (segment["spline_lower"], segment["spline_upper"])
        for segment in segments
        if segment["spline_lower"] is not None and segment["spline_upper"] is not None
    ]
    codes = np.asarray(context.comparison_unit_codes)
    # Clipped tails share support with their adjacent finite interval. A boundary
    # maximum alone must not make an otherwise supported curve disappear.
    masks = [_interval_membership(values, intervals, index) for index in range(len(intervals))]
    safe = [len(np.unique(codes[mask])) >= context.minimum_cell_size for mask in masks]
    if not all(safe):
        return MainEffectEvidence(
            feature=feature,
            semantic="native_component",
            source=_SOURCE,
            effect=pd.DataFrame({"x": [], "value": []}, dtype=float),
            suppression=SuppressionMetadata(
                status="partial" if any(safe) else "all",
                reason="minimum_support",
                presentation="curve_omitted",
            ),
        )
    finite_values = values[np.isfinite(values)]
    grid = np.unique(np.linspace(finite_values.min(), finite_values.max(), 200))
    with np.errstate(over="ignore", under="ignore"):
        relativities = np.exp(_spline_log_effect(segments, grid))
    if not np.all(np.isfinite(relativities) & (relativities > 0.0)):
        raise UnderwriterReportError(
            f"rating workbook spline {feature!r} produces invalid relativities"
        )
    weight = np.asarray(context.weight, dtype=float)
    return MainEffectEvidence(
        feature=feature,
        semantic="native_component",
        source=_SOURCE,
        effect=pd.DataFrame({"x": grid, "value": relativities}),
        density=pd.DataFrame(
            {
                "x": [lower + (upper - lower) / 2.0 for lower, upper in intervals],
                "density": [float(weight[mask].sum()) for mask in masks],
            }
        ),
    )


def _workbook_importance(blocks: dict[str, dict[str, Any]], context: ReportContext) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for feature, block in blocks.items():
        log_relativity = np.log(np.asarray(block["relativity"], dtype=float))
        weight = np.asarray(block["weight"], dtype=float)
        if "segments" in block:
            # The displayed exp(a) omits variation within each polynomial segment.
            # Measure exact log effects at the report observations instead.
            values = _numeric_context_values(context.frame[feature])
            assert values is not None  # Checked while collecting the main effect.
            valid = np.isfinite(values)
            log_relativity = _spline_log_effect(block["segments"], values[valid])
            weight = np.asarray(context.weight, dtype=float)[valid]
            if not len(weight) or not np.any(weight):
                records.append({"feature": feature, "magnitude": 0.0})
                continue
        mean = _weighted_mean(log_relativity, weight)
        variance = _weighted_mean(np.square(log_relativity - mean), weight)
        records.append({"feature": feature, "magnitude": variance})
    if not records:
        return pd.DataFrame(columns=["feature", "magnitude"])
    return pd.DataFrame(records).sort_values("magnitude", ascending=False, ignore_index=True)


__all__ = ["RatingWorkbookAdapter"]
