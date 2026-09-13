"""Records and declared limits shared by report adapters and evidence validation.

Adapters return ModelEvidence; ReportContext carries the aligned report inputs.
Collection and normalization live in evidence.py."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np
import pandas as pd

EvidenceSemantic = Literal[
    "native_component",
    "partial_dependence",
    "accumulated_local_effect",
    "shap_interaction",
    "portfolio_aggregate",
]


InteractionPlotKind = Literal[
    "surface",
    "categorical_heatmap",
    "varying_coefficient",
    "numeric_categorical",
    "numeric_numeric",
    "factor_smooth",
]


ExactLossSizeBasis = Literal["row_count", "weight_sum"]


SuppressionStatus = Literal["partial", "all"]


SuppressionReason = Literal["minimum_support"]


SuppressionPresentation = Literal["curve_omitted"]


MAX_SURFACE_CELLS = 25_600


MAX_INTERACTION_ROWS = 25_600


REQUIRED_INTERACTION_COLUMNS = {
    "surface": {"x", "y", "value"},
    "categorical_heatmap": {"left", "right", "value"},
    "varying_coefficient": {"x", "level", "value"},
    "numeric_categorical": {"level", "value"},
    "numeric_numeric": {"value"},
    "factor_smooth": {"x", "level", "value"},
}


_INTERACTION_COLUMN_ORDER = {
    "surface": ("x", "y", "value"),
    "categorical_heatmap": ("left", "right", "value"),
    "varying_coefficient": ("x", "level", "value"),
    "numeric_categorical": ("level", "value"),
    "numeric_numeric": ("value",),
    "factor_smooth": ("x", "level", "value"),
}


_CURVE_INTERACTION_KINDS = frozenset(
    {"varying_coefficient", "numeric_categorical", "numeric_numeric", "factor_smooth"}
)


_LEVEL_INTERACTION_KINDS = frozenset(
    {"varying_coefficient", "numeric_categorical", "factor_smooth"}
)


_LEVEL_DIAGNOSTIC_COLUMNS = (
    "level",
    "effective_df",
    "credibility",
    "has_information",
    "sufficient_support",
    "collapsed",
)


_SEMANTICS = frozenset(
    {
        "native_component",
        "partial_dependence",
        "accumulated_local_effect",
        "shap_interaction",
        "portfolio_aggregate",
    }
)


_INTERACTION_PLOT_KINDS = frozenset(
    {
        "surface",
        "categorical_heatmap",
        "varying_coefficient",
        "numeric_categorical",
        "numeric_numeric",
        "factor_smooth",
    }
)


_CAPABILITIES = frozenset({"importance", "main_effects", "interactions", "exact_loss"})


_SIZE_BASES = frozenset({"row_count", "weight_sum"})


_PROBLEM_POWERS = {"frequency": 1.0, "severity": 2.0}


@dataclass(frozen=True)
class ReportContext:
    """Aligned report inputs and aggregation limits supplied to evidence adapters."""

    frame: pd.DataFrame
    actual: np.ndarray
    predictions: Mapping[str, np.ndarray]
    weight: np.ndarray
    features: tuple[str, ...]
    comparison_unit_codes: np.ndarray
    comparison_units: int
    minimum_cell_size: int
    problem_type: Literal["frequency", "severity", "burn_cost"]
    deviance_power: float
    offset: np.ndarray | None = None


@dataclass(frozen=True)
class EvidenceFact:
    """A named scalar fact an adapter supplies for display alongside model diagnostics."""

    label: str
    value: str | int | float | bool | None


@dataclass(frozen=True)
class CapabilityUnavailable:
    """A report section the adapter cannot supply, with a reason to show the reader."""

    capability: Literal["importance", "main_effects", "interactions", "exact_loss"]
    reason: str


@dataclass(frozen=True)
class FeatureImportanceEvidence:
    """A feature-importance table with the method and source needed to interpret it."""

    table: pd.DataFrame
    method: str
    source: str


@dataclass(frozen=True)
class SuppressionMetadata:
    """The reason a report hides or limits a result with insufficient reporting support."""

    status: SuppressionStatus
    reason: SuppressionReason
    presentation: SuppressionPresentation


@dataclass(frozen=True)
class MainEffectEvidence:
    """One feature's relativity or contribution, with optional density and smoothness information."""

    feature: str
    semantic: EvidenceSemantic
    effect: pd.DataFrame
    source: str
    density: pd.DataFrame | None = None
    effective_df: float | None = None
    facts: tuple[EvidenceFact, ...] = ()
    warnings: tuple[str, ...] = ()
    suppression: SuppressionMetadata | None = None


@dataclass(frozen=True)
class InteractionEvidence:
    """A two-feature contribution table and the axes/support needed to plot it."""

    name: str
    parents: tuple[str, str]
    semantic: EvidenceSemantic
    plot_kind: InteractionPlotKind
    effect: pd.DataFrame
    source: str
    grid_axes: Mapping[str, np.ndarray] = field(default_factory=dict)
    density: pd.DataFrame | None = None
    support: pd.DataFrame | None = None
    default_levels: tuple[str, ...] = ()
    level_diagnostics: pd.DataFrame | None = None
    facts: tuple[EvidenceFact, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExactLossEvidence:
    """Likelihood contributions and fitted distribution metadata needed for comparable loss scores."""

    contributions: np.ndarray
    size_basis: ExactLossSizeBasis
    comparison_group: str
    score_label: str
    source: str
    family: str
    tweedie_power: float | None
    dispersion: float | None
    facts: tuple[EvidenceFact, ...] = ()


@dataclass(frozen=True)
class ModelEvidence:
    """One model's normalized diagnostics, relativities and metadata supplied to reporting."""

    source: str
    importance: FeatureImportanceEvidence | None = None
    main_effects: Mapping[str, MainEffectEvidence] = field(default_factory=dict)
    interactions: Mapping[str, InteractionEvidence] = field(default_factory=dict)
    exact_loss: ExactLossEvidence | None = None
    facts: tuple[EvidenceFact, ...] = ()
    warnings: tuple[str, ...] = ()
    unavailable: tuple[CapabilityUnavailable, ...] = ()


class ModelEvidenceAdapter(Protocol):
    """Adapter interface: collect model-specific evidence using the supplied report context."""

    def collect(
        self,
        *,
        model_name: str,
        source: object,
        context: ReportContext,
    ) -> ModelEvidence:
        raise NotImplementedError


@dataclass(frozen=True)
class EvidenceRequest:
    """A model name, artifact and adapter for ``collect_model_evidence`` to evaluate."""

    model_name: str
    adapter: ModelEvidenceAdapter
    source: object
