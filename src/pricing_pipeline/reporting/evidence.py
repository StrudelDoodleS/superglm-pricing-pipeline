"""Collect model evidence and normalize it before report calculations.

Start with collect_model_evidence: validate the report context, collect adapter
results, normalize each model and merge compatible evidence. Record definitions
live in evidence_types; interaction validation lives in interaction_evidence.
Existing public type imports remain available here."""

from __future__ import annotations

import math
from collections.abc import (
    Mapping,
    Sequence,
)
from dataclasses import (
    replace,
)
from types import (
    MappingProxyType,
)

import numpy as np
import pandas as pd

from pricing_pipeline.reporting.evidence_types import (
    _CAPABILITIES,
    _LEVEL_INTERACTION_KINDS,
    _PROBLEM_POWERS,
    _SIZE_BASES,
    MAX_INTERACTION_ROWS,
    MAX_SURFACE_CELLS,
    REQUIRED_INTERACTION_COLUMNS,
    CapabilityUnavailable,
    EvidenceFact,
    EvidenceRequest,
    EvidenceSemantic,
    ExactLossEvidence,
    ExactLossSizeBasis,
    FeatureImportanceEvidence,
    InteractionEvidence,
    InteractionPlotKind,
    MainEffectEvidence,
    ModelEvidence,
    ModelEvidenceAdapter,
    ReportContext,
    SuppressionMetadata,
    SuppressionPresentation,
    SuppressionReason,
    SuppressionStatus,
)
from pricing_pipeline.reporting.evidence_values import (
    _context_category_labels,
    _data_frame,
    _normalize_facts,
    _normalize_warnings,
    _numeric_column,
    _numeric_vector,
    _optional_finite_number,
    _plain_text,
    _semantic,
    _text_column,
    _validate_context,
    _validate_model_name,
)
from pricing_pipeline.reporting.inputs import (
    MAX_MAIN_EFFECT_GRID_POINTS,
    MAX_SURFACE_AXIS_POINTS,
)
from pricing_pipeline.reporting.interaction_evidence import (
    normalize_interaction_evidence,
)


def collect_model_evidence(
    context: ReportContext,
    direct: Mapping[str, ModelEvidence],
    requests: Sequence[EvidenceRequest],
) -> dict[str, ModelEvidence]:
    """Collect and compose direct evidence with adapter-produced evidence."""
    _validate_context(context)
    if not isinstance(direct, Mapping):
        raise TypeError("direct must be a mapping of model names to ModelEvidence")

    grouped: dict[str, list[ModelEvidence]] = {}
    for model_name, evidence in direct.items():
        _validate_model_name(model_name, context)
        _require_model_evidence(evidence)
        grouped.setdefault(model_name, []).append(
            normalize_model_evidence(model_name, evidence, context)
        )

    for request in requests:
        if not isinstance(request, EvidenceRequest):
            raise TypeError("requests must contain EvidenceRequest values")
        _validate_model_name(request.model_name, context)
        evidence = request.adapter.collect(
            model_name=request.model_name,
            source=request.source,
            context=context,
        )
        _require_model_evidence(evidence)
        grouped.setdefault(request.model_name, []).append(
            normalize_model_evidence(request.model_name, evidence, context)
        )

    return {
        model_name: normalize_model_evidence(
            model_name,
            _prepare_evidence_for_renormalization(_merge_evidence(model_name, values)),
            context,
        )
        for model_name, values in grouped.items()
    }


def normalize_model_evidence(
    model_name: str,
    evidence: ModelEvidence,
    context: ReportContext,
) -> ModelEvidence:
    """Validate evidence and detach all tabular and array values from callers."""
    _validate_context(context)
    _validate_model_name(model_name, context)
    _require_model_evidence(evidence)
    source = _plain_text(evidence.source, "source")
    importance = _normalize_importance(evidence.importance)
    main_effects = _normalize_main_effects(evidence.main_effects, context)
    interactions, unavailable_interactions = _normalize_interactions(
        model_name, evidence.interactions, context
    )
    if interactions:
        unavailable_interactions = ()
    exact_loss = _normalize_exact_loss(evidence.exact_loss, context)
    normalized = ModelEvidence(
        source=source,
        importance=importance,
        main_effects=MappingProxyType(main_effects),
        interactions=MappingProxyType(interactions),
        exact_loss=exact_loss,
        facts=_normalize_facts(evidence.facts),
        warnings=_normalize_warnings(evidence.warnings),
        unavailable=_normalize_unavailable(evidence.unavailable),
    )
    _validate_availability_consistency(normalized)
    return replace(
        normalized,
        unavailable=normalized.unavailable + unavailable_interactions,
    )


def _merge_evidence(model_name: str, values: Sequence[ModelEvidence]) -> ModelEvidence:
    if not values:
        raise ValueError(f"no evidence supplied for model {model_name!r}")
    merged = values[0]
    for next_evidence in values[1:]:
        for capability in ("importance", "main_effects", "interactions", "exact_loss"):
            if _is_populated(merged, capability) and _is_populated(next_evidence, capability):
                raise ValueError(
                    f"conflicting evidence for model {model_name!r} capability {capability!r}"
                )
        candidate = ModelEvidence(
            source=merged.source,
            importance=merged.importance or next_evidence.importance,
            main_effects=merged.main_effects or next_evidence.main_effects,
            interactions=merged.interactions or next_evidence.interactions,
            exact_loss=merged.exact_loss or next_evidence.exact_loss,
            facts=tuple(merged.facts) + tuple(next_evidence.facts),
            warnings=tuple(merged.warnings) + tuple(next_evidence.warnings),
            unavailable=tuple(merged.unavailable) + tuple(next_evidence.unavailable),
        )
        merged = replace(
            candidate,
            unavailable=tuple(
                item
                for item in candidate.unavailable
                if not _is_populated(candidate, item.capability)
            ),
        )
    return merged


def _prepare_evidence_for_renormalization(evidence: ModelEvidence) -> ModelEvidence:
    interactions = {
        name: replace(interaction, support=None, default_levels=())
        for name, interaction in evidence.interactions.items()
    }
    return replace(evidence, interactions=interactions)


def _is_populated(evidence: ModelEvidence, capability: str) -> bool:
    value = getattr(evidence, capability)
    return bool(value) if isinstance(value, Mapping) else value is not None


def _normalize_importance(
    importance: FeatureImportanceEvidence | None,
) -> FeatureImportanceEvidence | None:
    if importance is None:
        return None
    if not isinstance(importance, FeatureImportanceEvidence):
        raise TypeError("importance must be FeatureImportanceEvidence")
    table = _data_frame(importance.table, "importance.table")
    required = {"feature", "magnitude"}
    missing = required - set(table.columns)
    if missing:
        raise ValueError("importance.table is missing columns: " + ", ".join(sorted(missing)))
    permitted = ["feature", "magnitude", "effective_df"]
    table = table.loc[:, [column for column in permitted if column in table.columns]].copy(
        deep=True
    )
    table["feature"] = _text_column(table["feature"], "importance.table.feature")
    magnitudes = _numeric_column(table["magnitude"], "importance.table.magnitude")
    if (magnitudes < 0.0).any():
        raise ValueError("importance.table.magnitude must be non-negative")
    table["magnitude"] = magnitudes
    if "effective_df" in table:
        table["effective_df"] = _numeric_column(
            table["effective_df"], "importance.table.effective_df"
        )
    total = float(magnitudes.sum())
    table["share"] = magnitudes / total if total else np.zeros(len(table), dtype=float)
    table["method"] = _plain_text(importance.method, "importance.method")
    table["source"] = _plain_text(importance.source, "importance.source")
    return FeatureImportanceEvidence(
        table=table,
        method=table["method"].iat[0]
        if not table.empty
        else _plain_text(importance.method, "importance.method"),
        source=table["source"].iat[0]
        if not table.empty
        else _plain_text(importance.source, "importance.source"),
    )


def _normalize_main_effects(
    main_effects: Mapping[str, MainEffectEvidence], context: ReportContext
) -> dict[str, MainEffectEvidence]:
    if not isinstance(main_effects, Mapping):
        raise TypeError("main_effects must be a mapping")
    normalized: dict[str, MainEffectEvidence] = {}
    for name, main_effect in main_effects.items():
        key = _plain_text(name, "main_effects key")
        if not isinstance(main_effect, MainEffectEvidence):
            raise TypeError("main_effects values must be MainEffectEvidence")
        feature = _plain_text(main_effect.feature, "main_effect.feature")
        if feature not in context.features:
            raise ValueError(f"main-effect feature {feature!r} is not an allowed feature")
        if key != feature:
            raise ValueError("main_effects keys must match MainEffectEvidence.feature")
        semantic = _semantic(main_effect.semantic, "main_effect.semantic")
        effect = _data_frame(main_effect.effect, "main_effect.effect")
        if "value" not in effect:
            raise ValueError("main_effect.effect must include value")
        has_x = "x" in effect
        has_label = "label" in effect
        if has_x == has_label:
            raise ValueError("main_effect.effect requires exactly one of x or label")
        values = _numeric_column(effect["value"], "main_effect.effect.value")
        if semantic == "native_component" and (values <= 0.0).any():
            raise ValueError("native_component values must be finite and positive")
        coordinate = "x" if has_x else "label"
        permitted = [coordinate, "value", "lower", "upper"]
        effect = effect.loc[:, [column for column in permitted if column in effect]].copy(deep=True)
        effect["value"] = values
        density: pd.DataFrame | None
        if has_x:
            _validate_grid_size(len(effect), "main_effect.effect")
            effect["x"] = _numeric_column(effect["x"], "main_effect.effect.x")
            density = _normalize_numeric_density(main_effect.density)
        else:
            effect["label"] = _text_column(effect["label"], "main_effect.effect.label")
            density = _categorical_support(feature, effect["label"], context)
        _validate_bounds(effect)
        effective_df = _optional_finite_number(main_effect.effective_df, "main_effect.effective_df")
        suppression = _normalize_suppression(main_effect.suppression)
        if suppression is not None and (not effect.empty or density is not None):
            raise ValueError("suppressed main effects must omit the entire effect and density")
        normalized[key] = MainEffectEvidence(
            feature=feature,
            semantic=semantic,
            effect=effect,
            source=_plain_text(main_effect.source, "main_effect.source"),
            density=density,
            effective_df=effective_df,
            facts=_normalize_facts(main_effect.facts),
            warnings=_normalize_warnings(main_effect.warnings),
            suppression=suppression,
        )
    return normalized


def _normalize_suppression(value: object) -> SuppressionMetadata | None:
    if value is None:
        return None
    if not isinstance(value, SuppressionMetadata):
        raise TypeError("main_effect.suppression must be SuppressionMetadata")
    if value.status not in {"partial", "all"}:
        raise ValueError("main_effect.suppression.status is invalid")
    if value.reason != "minimum_support":
        raise ValueError("main_effect.suppression.reason is invalid")
    if value.presentation != "curve_omitted":
        raise ValueError("main_effect.suppression.presentation is invalid")
    return value


def _normalize_numeric_density(density: pd.DataFrame | None) -> pd.DataFrame | None:
    if density is None:
        return None
    density = _data_frame(density, "main_effect.density")
    if set(density.columns) != {"x", "density"}:
        raise ValueError("main_effect.density must contain exactly x and density")
    density = density.loc[:, ["x", "density"]].copy(deep=True)
    _validate_grid_size(len(density), "main_effect.density")
    density["x"] = _numeric_column(density["x"], "main_effect.density.x")
    values = _numeric_column(density["density"], "main_effect.density.density")
    if (values < 0.0).any():
        raise ValueError("main_effect.density.density must be non-negative")
    density["density"] = values
    return density


def _categorical_support(feature: str, labels: pd.Series, context: ReportContext) -> pd.DataFrame:
    values = _context_category_labels(feature, context)
    codes = np.asarray(context.comparison_unit_codes)
    weights = np.asarray(context.weight, dtype=float)
    masks = [values.eq(label).to_numpy() for label in labels]
    support = [int(np.unique(codes[mask]).size) for mask in masks]
    exposure = [float(weights[mask].sum()) for mask in masks]
    return pd.DataFrame(
        {
            "label": labels.to_numpy(copy=True),
            "comparison_units": support,
            "exposure": exposure,
        }
    )


def _validate_grid_size(size: int, name: str) -> None:
    if size > MAX_MAIN_EFFECT_GRID_POINTS:
        raise ValueError(f"{name} must contain at most {MAX_MAIN_EFFECT_GRID_POINTS} points")


def _validate_bounds(effect: pd.DataFrame) -> None:
    has_lower = "lower" in effect
    has_upper = "upper" in effect
    if has_lower != has_upper:
        raise ValueError("main_effect.effect lower and upper must appear together")
    if not has_lower:
        return
    lower = _numeric_column(effect["lower"], "main_effect.effect.lower")
    upper = _numeric_column(effect["upper"], "main_effect.effect.upper")
    value = effect["value"].to_numpy(dtype=float, copy=False)
    if (lower > value).any() or (value > upper).any():
        raise ValueError("main_effect.effect lower and upper must bracket value")
    effect["lower"] = lower
    effect["upper"] = upper


def _normalize_interactions(
    model_name: str,
    interactions: Mapping[str, InteractionEvidence],
    context: ReportContext,
) -> tuple[dict[str, InteractionEvidence], tuple[CapabilityUnavailable, ...]]:
    if not isinstance(interactions, Mapping):
        raise TypeError("interactions must be a mapping")
    normalized: dict[str, InteractionEvidence] = {}
    unavailable: list[CapabilityUnavailable] = []
    for key, interaction in interactions.items():
        key = _plain_text(key, "interactions key")
        if not isinstance(interaction, InteractionEvidence):
            raise TypeError("interactions values must be InteractionEvidence")
        name = _plain_text(interaction.name, "interaction.name")
        if name != key:
            raise ValueError("interactions keys must match InteractionEvidence.name")
        normalized_interaction = normalize_interaction_evidence(model_name, interaction, context)
        if (
            normalized_interaction.plot_kind in _LEVEL_INTERACTION_KINDS | {"categorical_heatmap"}
            and normalized_interaction.effect.empty
        ):
            unavailable.append(
                CapabilityUnavailable(
                    capability="interactions",
                    reason=f"{name}: no cells meet minimum support",
                )
            )
            continue
        normalized[key] = normalized_interaction
    return normalized, tuple(unavailable)


def _normalize_exact_loss(
    exact_loss: ExactLossEvidence | None, context: ReportContext
) -> ExactLossEvidence | None:
    if exact_loss is None:
        return None
    if not isinstance(exact_loss, ExactLossEvidence):
        raise TypeError("exact_loss must be ExactLossEvidence")
    contributions = _numeric_vector(exact_loss.contributions, "exact_loss.contributions")
    if len(contributions) != len(context.actual):
        raise ValueError("exact_loss.contributions must match context.actual length")
    if exact_loss.size_basis not in _SIZE_BASES:
        raise ValueError("exact_loss.size_basis must be row_count or weight_sum")
    power = _optional_finite_number(exact_loss.tweedie_power, "exact_loss.tweedie_power")
    dispersion = _optional_finite_number(exact_loss.dispersion, "exact_loss.dispersion")
    if dispersion is not None and dispersion <= 0.0:
        raise ValueError("exact_loss.dispersion must be positive")
    family = _plain_text(exact_loss.family, "exact_loss.family")
    _validate_loss_compatibility(family, power, context)
    return ExactLossEvidence(
        contributions=contributions,
        size_basis=exact_loss.size_basis,
        comparison_group=_plain_text(exact_loss.comparison_group, "exact_loss.comparison_group"),
        score_label=_plain_text(exact_loss.score_label, "exact_loss.score_label"),
        source=_plain_text(exact_loss.source, "exact_loss.source"),
        family=family,
        tweedie_power=power,
        dispersion=dispersion,
        facts=_normalize_facts(exact_loss.facts),
    )


def _validate_loss_compatibility(family: str, power: float | None, context: ReportContext) -> None:
    expected_family = {
        "frequency": "poisson",
        "severity": "gamma",
        "burn_cost": "tweedie",
    }[context.problem_type]
    if family.casefold() != expected_family:
        raise ValueError(
            f"exact_loss.family {family!r} is incompatible with {context.problem_type!r}"
        )
    if context.problem_type == "burn_cost":
        if power is None or not 1.0 < power < 2.0:
            raise ValueError("burn_cost exact_loss.tweedie_power must be between 1 and 2")
        return
    expected_power = _PROBLEM_POWERS[context.problem_type]
    if power is not None and not math.isclose(power, expected_power):
        raise ValueError(
            f"{context.problem_type} exact_loss.tweedie_power must equal {expected_power:g}"
        )


def _normalize_unavailable(
    unavailable: Sequence[CapabilityUnavailable],
) -> tuple[CapabilityUnavailable, ...]:
    normalized: list[CapabilityUnavailable] = []
    for item in unavailable:
        if not isinstance(item, CapabilityUnavailable):
            raise TypeError("unavailable must contain CapabilityUnavailable values")
        if item.capability not in _CAPABILITIES:
            raise ValueError("unavailable capability is invalid")
        normalized.append(
            CapabilityUnavailable(
                capability=item.capability,
                reason=_plain_text(item.reason, "unavailable.reason"),
            )
        )
    return tuple(normalized)


def _validate_availability_consistency(evidence: ModelEvidence) -> None:
    for item in evidence.unavailable:
        if _is_populated(evidence, item.capability):
            raise ValueError(f"{item.capability} capability is populated and declared unavailable")


def _require_model_evidence(evidence: object) -> None:
    if not isinstance(evidence, ModelEvidence):
        raise TypeError("evidence must be ModelEvidence")


__all__ = [
    "MAX_INTERACTION_ROWS",
    "MAX_MAIN_EFFECT_GRID_POINTS",
    "MAX_SURFACE_AXIS_POINTS",
    "MAX_SURFACE_CELLS",
    "REQUIRED_INTERACTION_COLUMNS",
    "CapabilityUnavailable",
    "EvidenceFact",
    "EvidenceRequest",
    "EvidenceSemantic",
    "ExactLossEvidence",
    "ExactLossSizeBasis",
    "FeatureImportanceEvidence",
    "InteractionEvidence",
    "InteractionPlotKind",
    "MainEffectEvidence",
    "ModelEvidence",
    "ModelEvidenceAdapter",
    "ReportContext",
    "SuppressionMetadata",
    "SuppressionPresentation",
    "SuppressionReason",
    "SuppressionStatus",
    "collect_model_evidence",
    "normalize_interaction_evidence",
    "normalize_model_evidence",
]
