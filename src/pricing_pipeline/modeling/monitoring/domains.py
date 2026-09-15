"""Read bounded feature domains without restoring fitted estimator objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from pricing_pipeline.modeling.recipes.superglm import decode_feature


@dataclass(frozen=True)
class SplineDomain:
    """Saved spline geometry needed by preflight, without basis or coefficients."""

    fitted_boundary: tuple[float, float]
    fitted_knots: np.ndarray
    extrapolation: str

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> SplineDomain:
        return cls(
            tuple(metadata["fitted"]["boundary"]),
            np.asarray(metadata["fitted"]["knots"], dtype=float),
            metadata["declared"]["extrapolation"],
        )


@dataclass(frozen=True)
class GroupingDomain:
    """The saved mapping from source labels to declared groups."""

    original_to_group: dict[str, str]
    group_to_originals: dict[str, list[str]]
    all_original_levels: list[str]

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any] | None) -> GroupingDomain | None:
        if metadata is None:
            return None
        return cls(
            metadata["original_to_group"],
            {group: metadata["group_to_originals"][group] for group in metadata["grouped_levels"]},
            metadata["all_original_levels"],
        )


@dataclass(frozen=True)
class CategoricalDomain:
    """A fitted categorical universe and its unknown-label policy."""

    levels: list[Any]
    grouping: GroupingDomain | None
    unseen: str

    def raw_domain(self, values: np.ndarray) -> tuple[list[Any], np.ndarray]:
        if self.grouping is None:
            return self.levels, values
        fitted_groups = set(self.levels)
        allowed = [
            level
            for level in self.grouping.all_original_levels
            if self.grouping.original_to_group[level] in fitted_groups
        ]
        return allowed, np.asarray([str(value) for value in values], dtype=object)


@dataclass(frozen=True)
class OrderedDomain:
    """A saved ordered axis with constructor-only label normalization."""

    constructor: Any
    known_levels: list[Any]
    smooth_levels: list[Any]
    level_to_value: dict[Any, float]
    base_level: Any
    specials: list[Any]
    grouping: Any
    spline: Any

    @classmethod
    def from_native(cls, spec: Any) -> OrderedDomain:
        return cls(
            spec,
            sorted(spec._known_levels, key=str),
            spec._smooth_levels,
            spec._level_to_value,
            spec._base_level,
            spec._special_raw or [],
            spec._grouping,
            spec._spline,
        )

    def raw_domain(self, values: np.ndarray) -> tuple[list[Any], np.ndarray]:
        values = self.constructor._canonical(values)
        allowed = self.constructor._canonical(np.asarray(self.known_levels, dtype=object))
        if self.grouping is not None:
            values = np.asarray([str(value) for value in values], dtype=object)
            allowed = np.asarray([str(value) for value in allowed], dtype=object)
        return pd.unique(allowed).tolist(), values

    def smooth_mask(self, values: np.ndarray) -> np.ndarray:
        if not self.specials:
            return np.ones(len(values), dtype=bool)
        return ~self.constructor._special_mask(values).any(axis=1)

    def map_to_numeric(self, values: np.ndarray) -> np.ndarray:
        return pd.Series(values).map(self.level_to_value).to_numpy(dtype=float)


def sql_feature_domains(
    payload: dict[str, Any],
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    """Combine fitted receipt domains with validated, unfitted recipe constructors."""
    recipe = payload["recipe"]
    configured = {
        name: decode_feature(recipe["features"][name], f"features.{name}")
        for name in recipe["feature_order"]
    }
    terms = {
        term["source_term_name"]: term for term in payload["receipt"]["term_metadata"].values()
    }
    domains: dict[str, Any] = {}
    for name, constructor in configured.items():
        term = terms[name]
        kind = term["feature_kind"]
        if kind == "spline":
            domains[name] = SplineDomain.from_metadata(term)
        elif kind == "categorical":
            domains[name] = CategoricalDomain(
                term["fitted"]["levels"],
                GroupingDomain.from_metadata(term["declared"]["grouping"]),
                term["declared"]["unseen"],
            )
        elif kind == "ordered_categorical":
            grouping = GroupingDomain.from_metadata(term["declared"]["grouping"])
            effective = term["effective"]
            positions = effective["level_values"]
            if isinstance(positions, list):
                positions = {item["level"]: item["value"] for item in positions}
            smooth = [level for level in effective["ordered_levels"] if level in positions]
            known = set(smooth if grouping is None else grouping.all_original_levels)
            known.update(effective["special_levels"])
            domains[name] = OrderedDomain(
                constructor,
                sorted(known, key=str),
                smooth,
                positions,
                term["fitted"]["base_level"],
                term["declared"]["specials"] or [],
                grouping,
                SplineDomain.from_metadata(term["spline"]),
            )
        else:
            # Numeric and polynomial support checks need only the observed data.
            domains[name] = constructor
    return recipe["feature_order"], domains, configured
