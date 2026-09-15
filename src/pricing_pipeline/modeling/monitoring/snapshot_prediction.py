"""Exact additive scoring from explicit, versioned monitoring JSON."""

from __future__ import annotations

import math
import warnings
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
from superglm.distributions import Tweedie, clip_mu, weighted_log_likelihood
from superglm.features.ordered_categorical import _declared_matcher
from superglm.links import stabilize_eta
from superglm.model.input_validation import _finite_vector, check_weight_contract

from pricing_pipeline.modeling.monitoring.contracts import (
    MonitoringError,
    MonitoringRelativity,
    _canonical_json,
    _label_point_key,
)
from pricing_pipeline.modeling.recipes.superglm import decode_object


def scalar_value(identity: dict[str, Any]) -> Any:
    """Read only the scalar identity tags supported by monitoring."""
    if not isinstance(identity, dict) or set(identity) != {"type", "value"}:
        raise MonitoringError("invalid snapshot categorical identity")
    tag, value = identity["type"], identity["value"]
    types = {"string": str, "integer": int, "real": float, "boolean": bool}
    if tag in types and type(value) is types[tag]:
        if tag == "real" and not math.isfinite(value):
            raise MonitoringError("invalid snapshot categorical real")
        return value
    if tag == "timestamp" and isinstance(value, str):
        result = pd.Timestamp(value)
        if not pd.isna(result):
            return result
    raise MonitoringError(f"unsupported snapshot categorical identity {tag!r}")


def spline_effect(term: dict[str, Any], values: Any) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    breaks = np.asarray(term["breaks"], dtype=float)
    coefficients = np.asarray(term["coefficients"], dtype=float)
    lo, hi = breaks[0], breaks[-1]
    policy = term["extrapolation"]
    if policy == "error" and np.any((x < lo) | (x > hi)):
        raise ValueError(f"Spline values outside fitted boundary [{lo}, {hi}]")
    clipped = np.clip(x, lo, hi)
    index = np.clip(np.searchsorted(breaks, clipped, side="right") - 1, 0, len(breaks) - 2)
    u = (clipped - breaks[index]) / (breaks[index + 1] - breaks[index])
    c = coefficients[index]
    result = c[:, 0] + u * (c[:, 1] + u * (c[:, 2] + u * c[:, 3]))
    if policy == "extend":
        for mask, boundary, key in ((x < lo, lo, "left_tail"), (x > hi, hi, "right_tail")):
            if mask.any():
                z = (x[mask] - boundary) / (hi - lo)
                result[mask] = np.polynomial.polynomial.polyval(z, term[key])
    return result


def categorical_effect(term: dict[str, Any], values: Any) -> np.ndarray:
    values = np.asarray(values, dtype=object)
    if pd.isna(values).any():
        raise ValueError("Categorical column contains missing values")
    if term["kind"] == "ordered_categorical":
        match = _declared_matcher([scalar_value(item) for item in term["canonical_levels"]])
        values = np.asarray([match(value) for value in values], dtype=object)
    if term["string_inputs"]:
        values = pd.Series(values).astype(str).to_numpy()
    levels = [scalar_value(item["identity"]) for item in term["levels"]]
    indices = pd.Index(levels, dtype=object).get_indexer(values)
    unknown = indices < 0
    if unknown.any() and term["unseen"] != "base":
        raise ValueError(
            f"Encountered unseen categorical levels: {list(pd.unique(values[unknown]))}"
        )
    if unknown.any():
        warnings.warn(
            "Routing categorical levels unseen at fit to the base level", UserWarning, stacklevel=2
        )
    effects = np.asarray([item["log_effect"] for item in term["levels"]])
    result = np.zeros(len(values), dtype=float)
    result[~unknown] = effects[indices[~unknown]]
    return result


def predict(payload: dict[str, Any], X: pd.DataFrame, offset: Any = None) -> np.ndarray:
    if not isinstance(X, pd.DataFrame) or not X.columns.is_unique:
        raise ValueError("snapshot prediction requires a DataFrame with unique columns")
    prediction = payload["prediction"]
    eta = np.full(len(X), prediction["intercept"], dtype=float)
    for name in payload["recipe"]["feature_order"]:
        if name not in X:
            raise ValueError(f"Missing feature {name!r}")
        term = prediction["terms"][name]
        if term["kind"] in {"categorical", "ordered_categorical"}:
            eta += categorical_effect(term, X[name].to_numpy())
            continue
        values = _finite_vector(name, X[name], len(X))
        eta += (
            values * term["coefficient"]
            if term["kind"] == "numeric"
            else spline_effect(term, values)
        )
    if offset is not None:
        eta += _finite_vector("offset", offset, len(X))
    family = decode_object(prediction["family"], "family", "snapshot.family")
    link = decode_object(prediction["link"], "link", "snapshot.link")
    return clip_mu(link.inverse(stabilize_eta(eta, link)), family)


def metrics(payload, X, y, sample_weight=None, offset=None):
    """Use the same family, null fit, dispersion and weights as native metrics."""
    from superglm._utils import _explained_deviance, _validate_strict_prior_weights
    from superglm.model.fit_ops import _compute_null_mu

    prediction = payload["prediction"]
    family = decode_object(prediction["family"], "family", "snapshot.family")
    link = decode_object(prediction["link"], "link", "snapshot.link")
    semantics = prediction["weight_semantics"]
    observed = _finite_vector("y", y, len(X))
    weights = (
        np.ones(len(X))
        if sample_weight is None
        else _finite_vector("sample_weight", sample_weight, len(X))
    )
    if np.any(weights < 0) or not np.any(weights > 0):
        raise ValueError("sample_weight must be nonnegative with positive total weight")
    if isinstance(family, Tweedie) and semantics == "prior":
        weights = _validate_strict_prior_weights(weights, len(X))
    mu = predict(payload, X, offset)
    check_weight_contract(observed, weights, family, semantics)
    offset_values = np.zeros(len(X)) if offset is None else _finite_vector("offset", offset, len(X))
    null_mu = _compute_null_mu(
        observed, weights, offset_values, family, link, weight_semantics=semantics
    )
    deviance = float(np.sum(weights * family.deviance_unit(observed, mu)))
    null_deviance = float(np.sum(weights * family.deviance_unit(observed, null_mu)))
    return SimpleNamespace(
        deviance=deviance,
        null_deviance=null_deviance,
        explained_deviance=_explained_deviance(deviance, null_deviance, observed, null_mu, weights),
        log_likelihood=weighted_log_likelihood(
            family, observed, mu, weights, prediction["phi"], weight_semantics=semantics
        ),
    )


def relativities(payload: dict[str, Any], evaluation_grid) -> tuple[MonitoringRelativity, ...]:
    rows = []
    for name, grid in evaluation_grid.items():
        term = payload["prediction"]["terms"][name]
        kind, points = grid["kind"], grid["points"]
        if kind == "continuous":
            values = spline_effect(term, points)
        elif kind == "numeric":
            values = [term["coefficient"]]
        elif kind == "categorical":
            lookup = {
                _canonical_json(item["identity"]): item["log_relativity"]
                for item in term["report_levels"]
            }
            values = [lookup[_canonical_json(point["identity"])] for point in points]
        else:
            raise MonitoringError(f"unsupported snapshot evaluation kind {kind!r}")
        for point, value in zip(points, values, strict=True):
            numeric = float(point) if kind == "continuous" else None
            label = (
                str(point["label"])
                if kind == "categorical"
                else None
                if numeric is not None
                else str(point)
            )
            key = (
                _label_point_key({"level": point["identity"]})
                if kind == "categorical"
                else _canonical_json({"x": numeric} if numeric is not None else {"level": point})
            )
            rows.append(
                MonitoringRelativity(
                    name,
                    kind,
                    key,
                    label,
                    numeric,
                    float(np.exp(value)),
                    float(value),
                    math.isclose(value, 0.0, abs_tol=1e-12),
                )
            )
    return tuple(rows)
