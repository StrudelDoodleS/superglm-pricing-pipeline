"""Normalize interaction coordinates, reporting support and plot metadata.

Consume InteractionEvidence and ReportContext; return checked interaction
evidence with the requested support suppression. The model-evidence workflow
calls this for each interaction supplied by an adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

import numpy as np
import pandas as pd

from pricing_pipeline.reporting.evidence_types import (
    _CURVE_INTERACTION_KINDS,
    _INTERACTION_COLUMN_ORDER,
    _LEVEL_DIAGNOSTIC_COLUMNS,
    _LEVEL_INTERACTION_KINDS,
    MAX_INTERACTION_ROWS,
    MAX_SURFACE_CELLS,
    REQUIRED_INTERACTION_COLUMNS,
    EvidenceSemantic,
    InteractionEvidence,
    InteractionPlotKind,
    ReportContext,
)
from pricing_pipeline.reporting.evidence_values import (
    _array,
    _context_category_labels,
    _data_frame,
    _normalize_facts,
    _normalize_warnings,
    _numeric_column,
    _plain_text,
    _plot_kind,
    _semantic,
    _text_column,
    _validate_context,
    _validate_model_name,
)
from pricing_pipeline.reporting.inputs import MAX_SURFACE_AXIS_POINTS


def normalize_interaction_evidence(
    model_name: str,
    evidence: InteractionEvidence,
    context: ReportContext,
) -> InteractionEvidence:
    """Validate one interaction and derive privacy-safe reporting support."""
    _validate_context(context)
    _validate_model_name(model_name, context)
    if not isinstance(evidence, InteractionEvidence):
        raise TypeError("evidence must be InteractionEvidence")
    if evidence.support is not None:
        raise ValueError("interaction.support must be None before normalization")
    if not isinstance(evidence.default_levels, tuple):
        raise TypeError("interaction.default_levels must be a tuple")
    if evidence.default_levels:
        raise ValueError("interaction.default_levels must be empty before normalization")

    name = _plain_text(evidence.name, "interaction.name")
    parents = _interaction_parents(evidence.parents, context)
    semantic = _semantic(evidence.semantic, "interaction.semantic")
    plot_kind = _plot_kind(evidence.plot_kind)
    _validate_interaction_compatibility(plot_kind, semantic, parents, context)
    _validate_interaction_input_sizes(evidence, plot_kind)
    effect = _normalize_interaction_effect(evidence.effect, plot_kind, semantic)
    grid_axes, density = _normalize_interaction_grid(
        evidence.grid_axes,
        evidence.density,
        effect,
        plot_kind,
    )
    level_diagnostics = _normalize_level_diagnostics(
        evidence.level_diagnostics,
        plot_kind,
    )

    support = None
    default_levels: tuple[str, ...] = ()
    if plot_kind == "categorical_heatmap":
        effect, support = _suppress_categorical_pairs(effect, parents, context)
    elif plot_kind in _LEVEL_INTERACTION_KINDS:
        effect, support, default_levels, safe_levels = _suppress_categorical_levels(
            effect,
            parents,
            context,
        )
        if level_diagnostics is not None:
            level_diagnostics = level_diagnostics.loc[
                level_diagnostics["level"].isin(safe_levels)
            ].reset_index(drop=True)

    return replace(
        evidence,
        name=name,
        parents=parents,
        semantic=semantic,
        plot_kind=plot_kind,
        effect=effect,
        source=_plain_text(evidence.source, "interaction.source"),
        grid_axes=MappingProxyType(grid_axes),
        density=density,
        support=support,
        default_levels=default_levels,
        level_diagnostics=level_diagnostics,
        facts=_normalize_facts(evidence.facts),
        warnings=_normalize_warnings(evidence.warnings),
    )


def _interaction_parents(
    value: object,
    context: ReportContext,
) -> tuple[str, str]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("interaction.parents must contain exactly two features")
    parents = tuple(_plain_text(parent, "interaction.parent") for parent in value)
    for parent in parents:
        if parent not in context.features:
            raise ValueError(f"interaction parent {parent!r} is not allowed")
    if parents[0] == parents[1]:
        raise ValueError("interaction parents must be distinct")
    return parents


def _validate_interaction_compatibility(
    plot_kind: InteractionPlotKind,
    semantic: EvidenceSemantic,
    parents: tuple[str, str],
    context: ReportContext,
) -> None:
    if plot_kind == "factor_smooth" and semantic != "native_component":
        raise ValueError("factor_smooth interactions require native_component semantic")
    if plot_kind in {"surface", "numeric_numeric"}:
        if not all(_is_numeric_feature(parent, context) for parent in parents):
            raise ValueError(f"{plot_kind} interaction parents must be numeric")
    elif plot_kind in _LEVEL_INTERACTION_KINDS and not _is_numeric_feature(parents[0], context):
        raise ValueError(f"{plot_kind} interaction first parent must be numeric")


def _is_numeric_feature(feature: str, context: ReportContext) -> bool:
    values = context.frame[feature]
    return not pd.api.types.is_bool_dtype(values) and pd.api.types.is_numeric_dtype(values)


def _validate_interaction_input_sizes(
    evidence: InteractionEvidence,
    plot_kind: InteractionPlotKind,
) -> None:
    _validate_interaction_table_size(evidence.effect, "interaction.effect")
    if evidence.density is not None:
        _validate_interaction_table_size(evidence.density, "interaction.density")
    if plot_kind != "surface" or not isinstance(evidence.grid_axes, Mapping):
        return
    lengths: dict[str, int] = {}
    for axis in ("x", "y"):
        if axis not in evidence.grid_axes:
            continue
        try:
            size = len(evidence.grid_axes[axis])
        except TypeError:
            continue
        if size > MAX_SURFACE_AXIS_POINTS:
            raise ValueError(
                f"surface grid_axes must contain at most {MAX_SURFACE_AXIS_POINTS} points per axis"
            )
        lengths[axis] = size
    if set(lengths) == {"x", "y"} and lengths["x"] * lengths["y"] > MAX_SURFACE_CELLS:
        raise ValueError(f"surface grid must contain at most {MAX_SURFACE_CELLS:,} cells")


def _validate_interaction_table_size(value: object, name: str) -> None:
    if not isinstance(value, pd.DataFrame):
        raise TypeError(f"{name} must be a pandas DataFrame")
    if len(value) > MAX_INTERACTION_ROWS:
        raise ValueError(f"{name} must contain at most {MAX_INTERACTION_ROWS:,} rows")


def _normalize_interaction_effect(
    value: object,
    plot_kind: InteractionPlotKind,
    semantic: EvidenceSemantic,
) -> pd.DataFrame:
    effect = _data_frame(value, "interaction.effect")
    required = REQUIRED_INTERACTION_COLUMNS[plot_kind]
    missing = set(required) - set(effect.columns)
    if missing:
        raise ValueError("interaction.effect is missing columns: " + ", ".join(sorted(missing)))
    permitted = list(_INTERACTION_COLUMN_ORDER[plot_kind])
    if plot_kind in _CURVE_INTERACTION_KINDS:
        permitted.extend(("lower", "upper"))
    unknown = set(effect.columns) - set(permitted)
    if unknown:
        raise ValueError("interaction.effect has unknown columns: " + ", ".join(sorted(unknown)))
    effect = effect.loc[:, [column for column in permitted if column in effect]].copy(deep=True)

    for column in ("left", "right", "level"):
        if column in effect:
            effect[column] = _text_column(effect[column], f"interaction.effect.{column}")
    for column in ("x", "y", "value"):
        if column in effect:
            effect[column] = _numeric_column(effect[column], f"interaction.effect.{column}")

    _validate_interaction_bounds(effect)
    _validate_interaction_response(effect, semantic)
    _validate_interaction_coordinates(effect, plot_kind)
    return effect


def _validate_interaction_coordinates(
    effect: pd.DataFrame,
    plot_kind: InteractionPlotKind,
) -> None:
    if (
        plot_kind in {"varying_coefficient", "factor_smooth"}
        and effect.duplicated(["x", "level"]).any()
    ):
        raise ValueError(f"{plot_kind} interaction.effect must have unique coordinates")
    if plot_kind == "numeric_categorical" and effect["level"].duplicated().any():
        raise ValueError("numeric_categorical interaction.effect must have unique coordinates")
    if plot_kind == "numeric_numeric" and len(effect) != 1:
        raise ValueError("numeric_numeric interaction.effect must contain exactly one row")


def _validate_interaction_bounds(effect: pd.DataFrame) -> None:
    has_lower = "lower" in effect
    has_upper = "upper" in effect
    if has_lower != has_upper:
        raise ValueError("interaction.effect lower and upper must appear together")
    if not has_lower:
        return
    lower = _numeric_column(effect["lower"], "interaction.effect.lower")
    upper = _numeric_column(effect["upper"], "interaction.effect.upper")
    values = effect["value"].to_numpy(dtype=float, copy=False)
    if (lower > values).any() or (values > upper).any():
        raise ValueError("interaction.effect lower and upper must bracket value")
    effect["lower"] = lower
    effect["upper"] = upper


def _validate_interaction_response(
    effect: pd.DataFrame,
    semantic: EvidenceSemantic,
) -> None:
    columns = [column for column in ("value", "lower", "upper") if column in effect]
    values = effect.loc[:, columns].to_numpy(dtype=float, copy=False)
    if semantic == "native_component" and (values <= 0.0).any():
        raise ValueError("native_component interaction response values must be positive")
    if semantic in {"partial_dependence", "portfolio_aggregate"} and (values < 0.0).any():
        raise ValueError(f"{semantic} interaction response values must be non-negative")


def _normalize_interaction_grid(
    grid_axes: object,
    density: pd.DataFrame | None,
    effect: pd.DataFrame,
    plot_kind: InteractionPlotKind,
) -> tuple[dict[str, np.ndarray], pd.DataFrame | None]:
    if not isinstance(grid_axes, Mapping):
        raise TypeError("interaction.grid_axes must be a mapping")
    if plot_kind != "surface":
        if grid_axes:
            raise ValueError("interaction.grid_axes is only valid for surface")
        if density is not None:
            raise ValueError("interaction.density is only valid for surface")
        return {}, None
    if set(grid_axes) != {"x", "y"}:
        raise ValueError("surface grid_axes must contain exactly x and y")

    axes: dict[str, np.ndarray] = {}
    for axis in ("x", "y"):
        raw = pd.Series(_array(grid_axes[axis], f"interaction.grid_axes.{axis}"))
        normalized = _numeric_column(raw, f"interaction.grid_axes.{axis}")
        if len(normalized) > MAX_SURFACE_AXIS_POINTS:
            raise ValueError(
                f"surface grid_axes must contain at most {MAX_SURFACE_AXIS_POINTS} points per axis"
            )
        if len(normalized) == 0:
            raise ValueError("surface grid_axes must not be empty")
        if len(np.unique(normalized)) != len(normalized):
            raise ValueError("surface grid_axes must contain unique coordinates")
        axes[axis] = normalized

    cells = len(axes["x"]) * len(axes["y"])
    if cells > MAX_SURFACE_CELLS:
        raise ValueError(f"surface grid must contain at most {MAX_SURFACE_CELLS:,} cells")
    if effect.duplicated(["x", "y"]).any():
        raise ValueError("surface interaction.effect has duplicate grid coordinates")
    if (
        len(effect) != cells
        or set(effect["x"]) != set(axes["x"])
        or set(effect["y"]) != set(axes["y"])
    ):
        raise ValueError("surface grid_axes disagree with interaction.effect")

    return axes, _normalize_surface_density(density, effect)


def _normalize_surface_density(
    density: pd.DataFrame | None,
    effect: pd.DataFrame,
) -> pd.DataFrame | None:
    if density is None:
        return None
    density = _data_frame(density, "interaction.density")
    required = ["x", "y", "density", "hdr_mass"]
    if set(density.columns) != set(required):
        raise ValueError("interaction.density must contain exactly x, y, density, and hdr_mass")
    density = density.loc[:, required].copy(deep=True)
    for column in required:
        density[column] = _numeric_column(density[column], f"interaction.density.{column}")
    if (density["density"] < 0.0).any():
        raise ValueError("interaction.density.density must be non-negative")
    hdr_tolerance = 8.0 * np.finfo(float).eps
    if ((density["hdr_mass"] < -hdr_tolerance) | (density["hdr_mass"] > 1.0 + hdr_tolerance)).any():
        raise ValueError("interaction.density.hdr_mass must be between 0 and 1")
    density["hdr_mass"] = density["hdr_mass"].clip(0.0, 1.0)
    if density.duplicated(["x", "y"]).any() or _coordinate_pairs(density) != _coordinate_pairs(
        effect
    ):
        raise ValueError("interaction.density grid must match interaction.effect grid")
    return density


def _coordinate_pairs(frame: pd.DataFrame) -> set[tuple[float, float]]:
    return set(zip(frame["x"].tolist(), frame["y"].tolist(), strict=True))


def _normalize_level_diagnostics(
    value: pd.DataFrame | None,
    plot_kind: InteractionPlotKind,
) -> pd.DataFrame | None:
    if value is None:
        return None
    if plot_kind != "factor_smooth":
        raise ValueError("interaction.level_diagnostics is only valid for factor_smooth")
    diagnostics = _data_frame(value, "interaction.level_diagnostics")
    if "level" not in diagnostics:
        raise ValueError("interaction.level_diagnostics is missing columns: level")
    unknown = set(diagnostics.columns) - set(_LEVEL_DIAGNOSTIC_COLUMNS)
    if unknown:
        raise ValueError(
            "interaction.level_diagnostics has unknown columns: " + ", ".join(sorted(unknown))
        )
    columns = [column for column in _LEVEL_DIAGNOSTIC_COLUMNS if column in diagnostics]
    diagnostics = diagnostics.loc[:, columns].copy(deep=True)
    diagnostics["level"] = _text_column(diagnostics["level"], "interaction.level_diagnostics.level")
    if diagnostics["level"].duplicated().any():
        raise ValueError("interaction.level_diagnostics must contain unique levels")
    for column in ("effective_df", "credibility"):
        if column in diagnostics:
            diagnostics[column] = _numeric_column(
                diagnostics[column], f"interaction.level_diagnostics.{column}"
            )
    if "effective_df" in diagnostics and (diagnostics["effective_df"] < 0.0).any():
        raise ValueError("interaction.level_diagnostics.effective_df must be non-negative")
    if (
        "credibility" in diagnostics
        and ((diagnostics["credibility"] < 0.0) | (diagnostics["credibility"] > 1.0)).any()
    ):
        raise ValueError("interaction.level_diagnostics.credibility must be between 0 and 1")
    for column in ("has_information", "sufficient_support", "collapsed"):
        if column in diagnostics:
            if not pd.api.types.is_bool_dtype(diagnostics[column]):
                raise TypeError(f"interaction.level_diagnostics.{column} must be boolean")
            diagnostics[column] = diagnostics[column].to_numpy(dtype=bool, copy=True)
    return diagnostics


def _suppress_categorical_pairs(
    effect: pd.DataFrame,
    parents: tuple[str, str],
    context: ReportContext,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if effect.duplicated(["left", "right"]).any():
        raise ValueError("interaction.effect has duplicate categorical cells")
    left_values = _context_category_labels(parents[0], context)
    right_values = _context_category_labels(parents[1], context)
    masks = [
        (left_values.eq(left) & right_values.eq(right)).to_numpy()
        for left, right in effect.loc[:, ["left", "right"]].itertuples(index=False, name=None)
    ]
    support = _interaction_support(effect.loc[:, ["left", "right"]], masks, context)
    safe = support["comparison_units"] >= context.minimum_cell_size
    return (
        effect.loc[safe.to_numpy()].reset_index(drop=True),
        support.loc[safe].reset_index(drop=True),
    )


def _suppress_categorical_levels(
    effect: pd.DataFrame,
    parents: tuple[str, str],
    context: ReportContext,
) -> tuple[pd.DataFrame, pd.DataFrame, tuple[str, ...], set[str]]:
    levels = pd.Series(pd.unique(effect["level"]), dtype="object")
    parent_values = _context_category_labels(parents[1], context)
    masks = [parent_values.eq(level).to_numpy() for level in levels]
    coordinates = pd.DataFrame({"level": levels.to_numpy(copy=True)})
    support = _interaction_support(coordinates, masks, context)
    support = support.loc[support["comparison_units"] >= context.minimum_cell_size].reset_index(
        drop=True
    )
    safe_levels = set(support["level"])
    effect = effect.loc[effect["level"].isin(safe_levels)].reset_index(drop=True)
    ranked = support.sort_values("weight", ascending=False, kind="mergesort")
    default_levels = tuple(ranked["level"].head(6).tolist())
    return effect, support, default_levels, safe_levels


def _interaction_support(
    coordinates: pd.DataFrame,
    masks: list[np.ndarray],
    context: ReportContext,
) -> pd.DataFrame:
    codes = np.asarray(context.comparison_unit_codes)
    weights = np.asarray(context.weight, dtype=float)
    total_weight = float(weights.sum())
    support = coordinates.copy(deep=True)
    support["rows"] = [int(mask.sum()) for mask in masks]
    support["comparison_units"] = [int(np.unique(codes[mask]).size) for mask in masks]
    support["weight"] = [float(weights[mask].sum()) for mask in masks]
    support["weight_share"] = support["weight"] / total_weight
    return support
