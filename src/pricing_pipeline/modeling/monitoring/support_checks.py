"""Check effective feature support before estimating monitoring coefficients.

These are per-feature checks, not a test of joint model identifiability. Ordered
smooth groups must all retain support; continuous coverage losses are warnings
unless the feature is constant or has no observations inside the saved domain.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, NamedTuple

import numpy as np
import pandas as pd
from superglm.features.spline import _SplineBase

from pricing_pipeline.modeling.monitoring.contracts import MonitoringVariant


class SupportIssue(NamedTuple):
    """One support finding, appended to the snapshot's shared issues table."""

    severity: str
    code: str
    message: str
    rows: int = 0
    weight: float | None = None


def _effective(values: np.ndarray, weights: np.ndarray | None) -> np.ndarray:
    return values if weights is None else values[weights > 0]


def _level_preview(values: Any) -> str:
    """Keep long categorical domains readable in notebook exceptions."""
    values = list(values)
    suffix = f" ... ({len(values)} total)" if len(values) > 20 else ""
    return repr(values[:20]) + suffix


def _ordered_support_message(
    feature: str,
    spec: Any,
    configured: Any,
    raw_levels: list[Any],
    grouped_values: np.ndarray,
    effective: set[Any],
    absent: list[Any],
) -> str:
    """Show the saved feature definition and the observed support that blocks a refit."""
    ordered = sorted(spec._smooth_levels, key=spec._level_to_value.__getitem__)
    groups = spec._grouping.group_to_originals if spec._grouping is not None else {}
    grouping = (
        "; ".join(
            f"{name!r}: {_level_preview(members)}" for name, members in list(groups.items())[:20]
        )
        or "none"
    )
    if len(groups) > 20:
        grouping += f" ... ({len(groups)} groups total)"
    observed = set(grouped_values)
    zero_weight = [level for level in absent if level in observed]
    return "\n".join(
        [
            f"Cannot refit ordered feature {feature!r}.",
            f"Config: {configured!r}",
            f"Saved smooth positions (level, value): {_level_preview((level, spec._level_to_value[level]) for level in ordered)}",
            f"Saved base: {spec._base_level!r}; specials: {_level_preview(spec._special_raw or [])}",
            f"Grouping: {grouping}",
            f"Received raw levels: {_level_preview(raw_levels)}",
            f"Smooth groups with positive weight: {_level_preview(level for level in ordered if level in effective)}",
            f"No positive-weight observations: {_level_preview(absent)}",
            f"Present only on zero-weight rows: {_level_preview(zero_weight)}",
            (
                "Check the source data, filters and fitting weights. If the feature definition "
                "changed deliberately, build and review a revised baseline. This refit will not "
                "estimate the curve across missing groups."
            ),
        ]
    )


def numeric_support_issues(
    feature: str,
    spec: Any,
    configured: Any,
    values: np.ndarray,
    weights: np.ndarray | None,
    variant: MonitoringVariant,
) -> Iterator[SupportIssue]:
    """Check variation and, for splines, coverage of the saved numeric domain."""
    refitting = variant is not MonitoringVariant.STATIC_SCORE
    effective = _effective(values, weights)
    if refitting and np.unique(effective).size < 2:
        yield SupportIssue(
            "error",
            "CONSTANT_FEATURE",
            f"Feature {feature!r} has fewer than two distinct values with positive fitting weight. "
            "Its coefficient cannot be separated from the intercept; review the snapshot before refitting.",
        )
    if isinstance(spec, _SplineBase):
        yield from _spline_support_issues(feature, spec, configured, values, weights, variant)


def ordered_support_issues(
    feature: str,
    spec: Any,
    configured: Any,
    values: np.ndarray,
    weights: np.ndarray | None,
    variant: MonitoringVariant,
) -> Iterator[SupportIssue]:
    """Require support for whole smooth groups after mapping original labels once."""
    if not isinstance(getattr(spec, "_spline", None), _SplineBase):
        return
    raw_levels = pd.unique(values).tolist()
    if spec._grouping is not None:
        values = pd.Series(values).map(spec._grouping.original_to_group).to_numpy()
    effective = set(_effective(values, weights))
    absent = [level for level in spec._smooth_levels if level not in effective]
    if absent and variant is not MonitoringVariant.STATIC_SCORE:
        yield SupportIssue(
            "error",
            "MISSING_ORDERED_SUPPORT",
            _ordered_support_message(
                feature, spec, configured, raw_levels, values, effective, absent
            ),
        )
    # Specials have independent indicators and must not count as spline support.
    smooth = (
        ~spec._special_mask(values).any(axis=1) if spec.has_specials else np.ones(len(values), bool)
    )
    numeric = spec._map_to_numeric(values[smooth])
    smooth_weights = None if weights is None else weights[smooth]
    if not numeric.size:
        return
    yield from _spline_support_issues(
        feature,
        spec._spline,
        configured._spline_obj,
        numeric,
        smooth_weights,
        variant,
        ordered=True,
    )


def _spline_support_issues(
    feature: str,
    spec: _SplineBase,
    configured: _SplineBase,
    values: np.ndarray,
    weights: np.ndarray | None,
    variant: MonitoringVariant,
    *,
    ordered: bool = False,
) -> Iterator[SupportIssue]:
    """Apply the requested boundary policy and report gaps in baseline support."""
    lo, hi = spec.fitted_boundary
    tolerance = 1e-12 * max(1.0, abs(lo), abs(hi), abs(hi - lo))
    effective = _effective(values, weights)
    refitting = variant is not MonitoringVariant.STATIC_SCORE
    inside = (effective >= lo - tolerance) & (effective <= hi + tolerance)
    if refitting and not inside.any():
        yield SupportIssue(
            "error",
            "NO_SPLINE_OVERLAP",
            f"Spline feature {feature!r} has no positive-weight observations inside its saved "
            f"domain [{lo:g}, {hi:g}]. Review upstream data or establish a revised baseline "
            "before a controlled refit, including FULL_ADAPTIVE.",
        )

    # Adaptive fits retain explicit boundaries but may re-estimate data-driven ones.
    boundary = spec.fitted_boundary
    if variant is MonitoringVariant.FULL_ADAPTIVE:
        boundary = configured._explicit_boundary
        knots = configured._explicit_knots
        # SuperGLM's ordered spline places knots on unweighted level values;
        # continuous splines exclude zero-weight rows from learned geometry.
        geometry = values if ordered else effective
        if boundary is None and geometry.size:
            boundary = (float(geometry.min()), float(geometry.max()))
        if boundary is not None and knots is not None:
            outside_knots = knots[(knots < boundary[0]) | (knots > boundary[1])]
            if outside_knots.size:
                yield SupportIssue(
                    "error",
                    "SPLINE_KNOTS_OUT_OF_BOUNDS",
                    f"Spline feature {feature!r} retains declared knots {outside_knots.tolist()} "
                    f"outside its adaptive domain [{boundary[0]:g}, {boundary[1]:g}]. Review the "
                    "declared geometry before refitting; knots will not be silently moved.",
                )
    policy = (
        spec.extrapolation
        if variant is MonitoringVariant.STATIC_SCORE
        else configured.extrapolation
    )
    if boundary is not None:
        eval_lo, eval_hi = boundary
        eval_tolerance = 1e-12 * max(1.0, abs(eval_lo), abs(eval_hi), abs(eval_hi - eval_lo))
        outside = (values < eval_lo - eval_tolerance) | (values > eval_hi + eval_tolerance)
        if outside.any():
            yield SupportIssue(
                "error" if policy == "error" else "warning",
                "SPLINE_OUT_OF_BOUNDS",
                f"Spline feature {feature!r} has {int(outside.sum())} rows outside "
                f"[{eval_lo:g}, {eval_hi:g}]; extrapolation={policy!r}. "
                "Review the affected rows before interpreting the curve.",
                int(outside.sum()),
                None if weights is None else float(weights[outside].sum()),
            )
        evaluation = np.clip(effective, eval_lo, eval_hi) if policy == "clip" else effective
        if refitting and np.unique(evaluation).size < 2:
            yield SupportIssue(
                "error",
                "CONSTANT_SPLINE",
                f"Spline feature {feature!r} has fewer than two distinct fitting values after "
                f"extrapolation={policy!r}. The smooth cannot be estimated from this snapshot.",
            )

    if not refitting or not effective.size:
        return
    current_lo, current_hi = float(effective.min()), float(effective.max())
    if current_lo > lo + tolerance or current_hi < hi - tolerance:
        yield SupportIssue(
            "warning",
            "SPLINE_RANGE_LOSS",
            f"Spline feature {feature!r} now has positive-weight range [{current_lo:g}, {current_hi:g}] "
            f"against saved domain [{lo:g}, {hi:g}]. Parts of the saved curve have no new "
            "observations supporting them; review before interpreting changes there.",
        )
    if ordered:
        return  # Missing groups are checked on the declared axis, not arbitrary intervals.
    edges = np.unique(np.r_[lo, spec.fitted_knots, hi])
    edges = edges[(edges >= lo) & (edges <= hi)]
    counts, _ = np.histogram(effective[inside], bins=edges)
    empty = np.flatnonzero(counts == 0)
    if empty.size:
        intervals = [(float(edges[i]), float(edges[i + 1])) for i in empty[:10]]
        yield SupportIssue(
            "warning",
            "EMPTY_SPLINE_INTERVALS",
            f"Spline feature {feature!r} has {len(empty)} saved knot intervals without "
            f"positive-weight observations: {intervals}. Interior intervals are left-closed, "
            "right-open; the final interval includes its upper edge. Review gaps before refitting.",
        )
