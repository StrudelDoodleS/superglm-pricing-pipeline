"""Check monitoring inputs and compare categorical mixes before any model refit.

Compatibility errors block refits. Distribution changes are review warnings, not
proof of changed SQL definitions. Candidate references come from verified artifacts;
standalone fitted models need an explicit reference dataframe for drift checks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from numbers import Real
from typing import Any

import numpy as np
import pandas as pd
from superglm import Categorical, OrderedCategorical, SuperGLM

from pricing_pipeline.modeling.monitoring.baseline import _resolve_monitoring_baseline
from pricing_pipeline.modeling.monitoring.contracts import (
    MonitoringError,
    MonitoringVariant,
    _canonical_json,
    _categorical_scalar_identity,
)
from pricing_pipeline.modeling.monitoring.support_checks import (
    numeric_support_issues,
    ordered_support_issues,
)
from pricing_pipeline.workbench.core import Candidate

_ISSUE_COLUMNS = ("feature", "severity", "code", "message", "affected_rows", "affected_weight")
_DISTRIBUTION_COLUMNS = (
    "feature",
    "level_key",
    "level",
    "reference_rows",
    "current_rows",
    "reference_row_share",
    "current_row_share",
    "reference_weight",
    "current_weight",
    "reference_weight_share",
    "current_weight_share",
)
_DRIFT_COLUMNS = ("feature", "row_distance", "weight_distance", "threshold", "needs_review")


@dataclass
class MonitoringDataCheck:
    """Aggregate compatibility issues and categorical drift for one snapshot.

    Inspect ``issues``, ``distributions`` and ``drift`` as dataframes, then call
    ``raise_for_errors`` before the monitoring loop. ``to_json`` returns aggregate
    evidence for caller-managed logging; this report is not a SQL observation.
    """

    issues: pd.DataFrame
    distributions: pd.DataFrame
    drift: pd.DataFrame
    reference_source: str

    @property
    def compatible(self) -> bool:
        """Whether this check found no input errors for controlled refits."""
        return not bool(self.issues.severity.eq("error").any())

    @property
    def needs_review(self) -> bool:
        """Whether errors, missing support or drift warnings require attention."""
        return not self.issues.empty

    def raise_for_errors(self) -> None:
        """Stop before fitting if the report contains compatibility errors."""
        if not self.compatible:
            raise MonitoringDataError(self)

    def to_json(self) -> str:
        """Serialize aggregate evidence without source rows or predictions."""
        return json.dumps(
            {
                "compatible": self.compatible,
                "needs_review": self.needs_review,
                "reference_source": self.reference_source,
                **{
                    name: json.loads(
                        getattr(self, name).to_json(orient="records", double_precision=15)
                    )
                    for name in ("issues", "distributions", "drift")
                },
            },
            ensure_ascii=False,
            allow_nan=False,
        )


class MonitoringDataError(MonitoringError):
    """An incompatible snapshot, with its full preflight report attached."""

    def __init__(self, report: MonitoringDataCheck):
        self.report = report
        errors = report.issues.loc[report.issues.severity.eq("error")]
        super().__init__("Monitoring data is incompatible: " + "; ".join(errors.message))


def _issue(
    issues: list[dict[str, Any]],
    feature: str | None,
    severity: str,
    code: str,
    message: str,
    rows: int = 0,
    weight: float | None = None,
) -> None:
    issues.append(
        {
            "feature": feature,
            "severity": severity,
            "code": code,
            "message": message,
            "affected_rows": rows,
            "affected_weight": weight,
        }
    )


def _real_array(values: Any) -> np.ndarray:
    """Convert numeric inputs without silently dropping complex components."""
    raw = np.asarray(values)
    if np.iscomplexobj(raw) or (
        raw.dtype.kind == "O"
        and any(isinstance(value, complex | np.complexfloating) for value in raw.flat)
    ):
        raise ValueError("values must be real")
    return np.asarray(raw, dtype=float)


def _weights(df: pd.DataFrame, values: Any, issues: list[dict[str, Any]]) -> np.ndarray | None:
    if values is None:
        return None
    try:
        weights = _real_array(values)
        with np.errstate(over="ignore", invalid="ignore"):
            total = weights.sum()
        valid = (
            weights.ndim == 1
            and len(weights) == len(df)
            and np.isfinite(weights).all()
            and (weights >= 0).all()
            and np.isfinite(total)
            and total > 0
        )
    except TypeError, ValueError, OverflowError:
        valid = False
    if not valid:
        _issue(
            issues,
            None,
            "error",
            "INVALID_WEIGHTS",
            "sample_weight must be a finite, nonnegative vector aligned by row position, with positive total weight.",
        )
        return None
    return weights


def _categorical_domain(spec: Any, values: np.ndarray) -> tuple[list[Any], np.ndarray]:
    """Use the same raw-level spelling and grouping rules as the fitted feature."""
    grouping = getattr(spec, "_grouping", None)
    if isinstance(spec, OrderedCategorical):
        values = spec._canonical(values)
        allowed = spec._canonical(np.asarray(sorted(spec._known_levels, key=str), dtype=object))
        if grouping is not None:
            values = np.asarray([str(value) for value in values], dtype=object)
            allowed = np.asarray([str(value) for value in allowed], dtype=object)
        allowed = pd.unique(allowed).tolist()
    elif grouping is not None:
        fitted_groups = set(spec._levels)
        allowed = [
            level
            for level in grouping.all_original_levels
            if grouping.original_to_group[level] in fitted_groups
        ]
        values = np.asarray([str(value) for value in values], dtype=object)
    else:
        allowed = list(spec._levels)
    return allowed, values


def _inspect_features(
    baseline: SuperGLM,
    df: pd.DataFrame,
    sample_weight: Any,
    *,
    variant: MonitoringVariant | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, dict[str, Any]]]]:
    issues: list[dict[str, Any]] = []
    profiles: dict[str, dict[str, dict[str, Any]]] = {}
    if not isinstance(df, pd.DataFrame):
        _issue(issues, None, "error", "INVALID_DATA", "Monitoring data must be a pandas DataFrame.")
        return issues, profiles
    if df.empty:
        _issue(issues, None, "error", "EMPTY_DATA", "Monitoring data must not be empty.")
        return issues, profiles
    if not df.columns.is_unique:
        _issue(
            issues, None, "error", "DUPLICATE_COLUMNS", "Monitoring column names must be unique."
        )
        return issues, profiles
    weights = _weights(df, sample_weight, issues)
    if sample_weight is not None and weights is None:
        return issues, profiles
    configured = dict(baseline._config.feature_templates)
    weight_total = None if weights is None else float(weights.sum())
    for feature in baseline._feature_order:
        if feature not in df:
            _issue(issues, feature, "error", "MISSING_FEATURE", f"Feature {feature!r} is missing.")
            continue
        series = df[feature]
        spec = baseline._specs[feature]
        if (
            variant is not None
            and variant is not MonitoringVariant.STATIC_SCORE
            and feature not in configured
        ):
            _issue(
                issues,
                feature,
                "error",
                "MISSING_FEATURE_CONFIG",
                f"Feature {feature!r} has no saved explicit constructor configuration. "
                "Use STATIC_SCORE to score this baseline, or fit and review a baseline "
                "with explicitly configured features before running refits.",
            )
            continue
        # Legacy auto-detected features can still be scored from their fitted definitions.
        feature_config = configured.get(feature, spec)
        missing = series.isna().to_numpy()
        if missing.any():
            _issue(
                issues,
                feature,
                "error",
                "INVALID_VALUES",
                f"Feature {feature!r} contains null values; apply its declared missing-value mapping upstream.",
                int(missing.sum()),
            )
            continue
        if not isinstance(spec, (Categorical, OrderedCategorical)):
            try:
                if (
                    pd.api.types.is_complex_dtype(series.dtype)
                    or pd.api.types.is_datetime64_any_dtype(series.dtype)
                    or pd.api.types.is_timedelta64_dtype(series.dtype)
                ):
                    raise ValueError("expected real numeric values")
                numeric = _real_array(series)
                valid = True
                bad = ~np.isfinite(numeric)
            except TypeError, ValueError, OverflowError:
                valid, bad = False, np.ones(len(series), dtype=bool)
            if not valid or bad.any():
                _issue(
                    issues,
                    feature,
                    "error",
                    "INVALID_VALUES",
                    f"Feature {feature!r} requires finite numeric values.",
                    len(series) if not valid else int(bad.sum()),
                )
            elif variant is not None:
                for item in numeric_support_issues(
                    feature, spec, feature_config, numeric, weights, variant
                ):
                    _issue(issues, feature, *item)
            continue
        try:
            allowed, values = _categorical_domain(spec, series.to_numpy())
            # Preserve scalar identities in aggregate output; never merge 1 and "1".
            identities = [_categorical_scalar_identity(value) for value in allowed]
            codes = pd.Index(allowed, dtype=object).get_indexer(values)
        except (TypeError, ValueError, MonitoringError) as exc:
            _issue(
                issues,
                feature,
                "error",
                "INVALID_VALUES",
                f"Feature {feature!r} has invalid categorical values: {exc}",
                len(series),
            )
            continue
        unknown = codes < 0
        if unknown.any():
            fallback = (
                variant is MonitoringVariant.STATIC_SCORE
                and isinstance(spec, Categorical)
                and spec.unseen == "base"
                and spec._grouping is None
            )
            examples = list(dict.fromkeys(str(value) for value in values[unknown]))[:10]
            _issue(
                issues,
                feature,
                "warning" if fallback else "error",
                "UNKNOWN_LEVELS",
                f"Feature {feature!r} has levels outside the baseline raw-level universe: {examples}. "
                "Check upstream data or build a revised baseline; FULL_ADAPTIVE keeps these levels frozen.",
                int(unknown.sum()),
                None if weights is None else float(weights[unknown].sum()),
            )
            continue
        if isinstance(spec, OrderedCategorical) and variant is not None:
            for item in ordered_support_issues(
                feature, spec, feature_config, values, weights, variant
            ):
                _issue(issues, feature, *item)
        counts = np.bincount(codes, minlength=len(allowed))
        masses = (
            None if weights is None else np.bincount(codes, weights=weights, minlength=len(allowed))
        )
        support = counts if masses is None else masses
        absent = np.flatnonzero(support == 0)
        if len(absent):
            labels = [str(allowed[i]) for i in absent[:10]]
            _issue(
                issues,
                feature,
                "warning",
                "ABSENT_LEVELS",
                f"Feature {feature!r} has no fitting support for baseline levels {labels}. "
                "Review missing support before interpreting refitted relativities.",
            )
        profiles[feature] = {
            _canonical_json(identity): {
                "level": str(allowed[i]),
                "rows": int(counts[i]),
                "row_share": float(counts[i] / len(df)),
                "weight": None if masses is None else float(masses[i]),
                "weight_share": None if masses is None else float(masses[i] / weight_total),
            }
            for i, identity in enumerate(identities)
        }
    return issues, profiles


def _report(
    issues: list[dict[str, Any]],
    distributions: list[dict[str, Any]],
    drift: list[dict[str, Any]],
    reference_source: str,
) -> MonitoringDataCheck:
    return MonitoringDataCheck(
        pd.DataFrame(issues, columns=_ISSUE_COLUMNS),
        pd.DataFrame(distributions, columns=_DISTRIBUTION_COLUMNS),
        pd.DataFrame(drift, columns=_DRIFT_COLUMNS),
        reference_source,
    )


def _require_compatible_monitoring_data(
    baseline: SuperGLM,
    df: pd.DataFrame,
    sample_weight: Any,
    *,
    variant: MonitoringVariant,
) -> None:
    """Keep compatibility checks mandatory even when callers skip the drift report."""
    issues, _ = _inspect_features(baseline, df, sample_weight, variant=variant)
    _report(issues, [], [], "not_requested").raise_for_errors()


def check_monitoring_data(
    baseline_model: SuperGLM | Candidate,
    df: pd.DataFrame,
    *,
    sample_weight: Any = None,
    reference_df: pd.DataFrame | None = None,
    reference_sample_weight: Any = None,
    drift_threshold: float = 0.2,
    variant: MonitoringVariant | str = MonitoringVariant.FROZEN_REFIT,
) -> MonitoringDataCheck:
    """Check a snapshot once before running the controlled monitoring presets.

    Compare raw categorical/ordered levels against the fitted baseline. Unknown
    levels, invalid inputs, constant numeric features, unsupported ordered smooth
    groups and splines with no saved-domain overlap block refits. Partial continuous
    coverage losses and changed mixes warn. Extra columns are ignored. Weights follow
    dataframe row order. ``variant`` defaults to FROZEN_REFIT; STATIC_SCORE checks
    prediction compatibility without requiring support to estimate coefficients.

    A verified Candidate supplies reference inputs and fitting weights from its
    saved bundle. For a standalone SuperGLM, supply reference_df for drift checks.
    No reference means drift is explicitly unassessed. Total variation distance
    is half the sum of absolute level-share changes, from 0 to 1. The configurable
    default threshold of 0.2 is a review trigger, not a statistical significance
    test. Weight distances require weights on both sides. This checks categorical
    marginals; matching marginals cannot certify unchanged upstream semantics.
    """
    resolved_variant = MonitoringVariant(variant)
    if (
        isinstance(drift_threshold, bool)
        or not isinstance(drift_threshold, Real)
        or not np.isfinite(drift_threshold)
        or not 0 < drift_threshold <= 1
    ):
        raise ValueError("drift_threshold must be finite and in (0, 1].")
    if isinstance(baseline_model, Candidate) and (
        reference_df is not None or reference_sample_weight is not None
    ):
        raise ValueError(
            "Candidate reference inputs come from its verified artifact and cannot be overridden."
        )
    baseline, _, bundle = _resolve_monitoring_baseline(baseline_model)
    reference_source = "provided" if reference_df is not None else "unavailable"
    if bundle is not None:
        reference_source = "saved_candidate"
        reference_df = bundle.X
        reference_sample_weight = bundle.sample_weight if sample_weight is not None else None
    issues, current = _inspect_features(baseline, df, sample_weight, variant=resolved_variant)
    if reference_df is None:
        _issue(
            issues,
            None,
            "warning",
            "REFERENCE_UNAVAILABLE",
            "Categorical drift was not assessed: supply reference_df or a verified saved Candidate.",
        )
        return _report(issues, [], [], reference_source)
    reference_issues, reference = _inspect_features(baseline, reference_df, reference_sample_weight)
    for item in reference_issues:
        if item["severity"] == "error":
            issues.append({**item, "message": "Invalid reference data: " + item["message"]})
    weighted = sample_weight is not None and reference_sample_weight is not None
    if (sample_weight is None) != (reference_sample_weight is None):
        _issue(
            issues,
            None,
            "warning",
            "WEIGHT_REFERENCE_UNAVAILABLE",
            "Weighted drift was not assessed: both snapshots need comparable weights. Row-share drift is still reported.",
        )
    distributions, drift = [], []
    for feature, profile in current.items():
        if feature not in reference:
            continue
        row_distance, weight_distance = 0.0, 0.0 if weighted else None
        for key, now in profile.items():
            before = reference[feature][key]
            row_distance += abs(now["row_share"] - before["row_share"]) / 2
            if weighted and now["weight_share"] is not None and before["weight_share"] is not None:
                weight_distance += abs(now["weight_share"] - before["weight_share"]) / 2
            elif weighted:
                weight_distance = None
            distributions.append(
                {
                    "feature": feature,
                    "level_key": key,
                    "level": now["level"],
                    **{
                        f"{side}_{field}": values[field]
                        for side, values in (("reference", before), ("current", now))
                        for field in ("rows", "row_share", "weight", "weight_share")
                    },
                }
            )
        review = max(row_distance, weight_distance or 0.0) >= drift_threshold
        drift.append(
            {
                "feature": feature,
                "row_distance": row_distance,
                "weight_distance": weight_distance,
                "threshold": float(drift_threshold),
                "needs_review": review,
            }
        )
        if review:
            _issue(
                issues,
                feature,
                "warning",
                "CATEGORICAL_DRIFT",
                f"Feature {feature!r} has a large categorical mix change. Check upstream SQL definitions "
                "and portfolio composition; a new baseline may be needed. Drift alone does not identify the cause.",
            )
    return _report(issues, distributions, drift, reference_source)
