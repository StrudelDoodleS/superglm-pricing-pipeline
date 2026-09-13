"""Capture baseline structure and reconstruct the model allowed by a monitoring variant.

Preserve fitted categories, spline geometry and selected lambda policies here.
The workflow supplies the data and invokes fit_reml on the returned model."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from importlib.metadata import version as package_version
from typing import Any

import numpy as np
from superglm import SuperGLM
from superglm.features.categorical import Categorical
from superglm.features.constraint import ConstraintSpec
from superglm.features.numeric import Numeric
from superglm.features.ordered_categorical import OrderedCategorical
from superglm.features.polynomial import Polynomial
from superglm.features.spline import Spline, _SplineBase
from superglm.types import LambdaPolicy

from pricing_pipeline.modeling.monitoring.baseline import _require_fitted_superglm
from pricing_pipeline.modeling.monitoring.contracts import (
    FIT_CONTRACT_SCHEMA,
    FIT_CONTRACT_SCHEMA_VERSION,
    MONITORING_VARIANT_POLICIES,
    ModelFitContract,
    MonitoringError,
    MonitoringVariant,
    _canonical_json,
    _categorical_scalar_identity,
    _sha256_text,
)
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
    _spline_kind,
    build_superglm_publication_receipt,
)


def _evaluation_grid(
    model: SuperGLM,
    term_metadata: Mapping[str, Mapping[str, Any]],
    *,
    continuous_points: int,
) -> dict[str, dict[str, Any]]:
    if continuous_points < 2:
        raise ValueError("continuous_points must be at least 2")

    grids: dict[str, dict[str, Any]] = {}
    relativity_frames = model.relativities(with_se=False, centering="native")
    for metadata in term_metadata.values():
        kind = str(metadata["feature_kind"])
        if kind == "offset":
            continue
        source_name = str(metadata["source_term_name"])
        if kind in {"spline", "polynomial"}:
            fitted = metadata["fitted"]
            if kind == "spline":
                boundary = fitted.get("boundary")
            else:
                boundary = [fitted.get("lower_bound"), fitted.get("upper_bound")]
            if boundary is None or any(value is None for value in boundary):
                raise MonitoringError(f"term {source_name!r} has no fitted continuous boundary")
            points = np.linspace(float(boundary[0]), float(boundary[1]), continuous_points)
            grids[source_name] = {"kind": "continuous", "points": points.tolist()}
        elif kind in {"categorical", "ordered_categorical"}:
            inference = model.term_inference(source_name, with_se=False, centering="native")
            grids[source_name] = {
                "kind": "categorical",
                # Public inference expands a fitted grouping back to original
                # levels.  Those are the stable business-facing points to track,
                # not the internal group labels.
                "points": [
                    {
                        "identity": _categorical_scalar_identity(level),
                        "label": str(level),
                    }
                    for level in (inference.levels or [])
                ],
            }
        elif kind == "numeric":
            grids[source_name] = {"kind": "numeric", "points": ["per_unit"]}
        elif kind == "categorical_interaction":
            frame = relativity_frames.get(source_name)
            if frame is None or "level" not in frame:
                raise MonitoringError(
                    f"categorical interaction {source_name!r} has no stable level grid"
                )
            grids[source_name] = {
                "kind": "categorical_interaction",
                "points": frame["level"].tolist(),
            }
        else:
            raise MonitoringError(f"term {source_name!r} uses unsupported monitoring kind {kind!r}")
    return grids


def build_model_fit_contract(
    model: SuperGLM,
    *,
    offset_contract: OffsetExportContract | None = None,
    fit_sample_weight_name: str | None = None,
    export_weight_name: str | None = None,
    input_transforms: dict[str, dict[str, Any]] | None = None,
    continuous_points: int = 101,
) -> ModelFitContract:
    """Capture one fitted model's immutable structural and smoothing contract."""
    fitted = _require_fitted_superglm(model)
    resolved_offset = offset_contract or OffsetExportContract(handling="NONE")
    receipt = build_superglm_publication_receipt(
        fitted,
        offset_contract=resolved_offset,
        fit_sample_weight_name=fit_sample_weight_name,
        export_weight_name=export_weight_name,
        input_transforms=input_transforms,
    )
    telemetry = fitted.training_telemetry()
    lambdas = fitted.reml_diagnostics().get("lambdas", {})
    term_metadata = receipt.model_dump(mode="json")["term_metadata"]
    structure = {
        "model": telemetry["model"],
        "feature_schema": telemetry["features"],
        "package_metadata": receipt.model_dump(mode="json")["package_metadata"],
        "term_metadata": term_metadata,
        "always_frozen": [
            "family_and_link",
            "feature_order_and_types",
            "categorical_level_universes",
            "categorical_groupings",
            "categorical_bases_and_unseen_policy",
            "ordered_level_values_and_special_levels",
            "spline_kind_degree_dimension_and_penalty_order",
            "shape_and_monotonic_constraints",
            "caller_declared_explicit_knots_and_boundaries",
        ],
    }
    structure_json = _canonical_json(structure)
    payload = {
        "schema_name": FIT_CONTRACT_SCHEMA,
        "schema_version": FIT_CONTRACT_SCHEMA_VERSION,
        "superglm_version": package_version("superglm"),
        "structure_sha256": _sha256_text(structure_json),
        "structure": structure,
        "fitted_lambdas": dict(sorted((str(k), float(v)) for k, v in lambdas.items())),
        "evaluation_grid": _evaluation_grid(
            fitted,
            term_metadata,
            continuous_points=continuous_points,
        ),
        "variants": {
            variant.value: {
                "refit_coefficients": policy.refit_coefficients,
                "reestimate_lambdas": policy.reestimate_lambdas,
                "reposition_data_driven_knots": policy.reposition_data_driven_knots,
            }
            for variant, policy in MONITORING_VARIANT_POLICIES.items()
        },
    }
    contract_json = _canonical_json(payload)
    return ModelFitContract(
        contract_json=contract_json,
        contract_sha256=_sha256_text(contract_json),
        structure_sha256=payload["structure_sha256"],
        superglm_version=payload["superglm_version"],
    )


def _constraint(spec: _SplineBase) -> ConstraintSpec | None:
    kind = getattr(spec, "constraint_kind", None)
    if kind is None:
        return None
    return ConstraintSpec(mode=str(spec.constraint_mode), kind=str(kind))


def _fixed_lambda_policy(
    term_name: str,
    fitted_lambdas: Mapping[str, float],
    configured_policy: Any,
) -> LambdaPolicy | dict[str, LambdaPolicy] | None:
    direct = fitted_lambdas.get(term_name)
    if direct is not None:
        return LambdaPolicy.fixed(float(direct))
    components = {
        name.removeprefix(f"{term_name}:"): LambdaPolicy.fixed(float(value))
        for name, value in fitted_lambdas.items()
        if name.startswith(f"{term_name}:")
    }
    if components:
        return components
    global_lambda = fitted_lambdas.get("lambda2")
    if global_lambda is not None:
        return LambdaPolicy.fixed(float(global_lambda))
    return copy.deepcopy(configured_policy)


def _rebuild_spline(
    configured: _SplineBase,
    fitted: _SplineBase,
    *,
    term_name: str,
    freeze_geometry: bool,
    freeze_lambdas: bool,
    fitted_lambdas: Mapping[str, float],
) -> _SplineBase:
    if freeze_geometry:
        knots = fitted.fitted_knots
        boundary = fitted.fitted_boundary
    else:
        named_knots = getattr(configured, "_named_knots", None)
        explicit_knots = getattr(configured, "_explicit_knots", None)
        knots = named_knots if named_knots is not None else explicit_knots
        boundary = getattr(configured, "_explicit_boundary", None)

    configured_policy = getattr(configured, "_lambda_policy", None)
    lambda_policy = (
        _fixed_lambda_policy(term_name, fitted_lambdas, configured_policy)
        if freeze_lambdas
        else copy.deepcopy(configured_policy)
    )
    m_orders = tuple(int(value) for value in configured._m_orders)
    m: int | tuple[int, ...] = m_orders[0] if len(m_orders) == 1 else m_orders
    return Spline(
        kind=_spline_kind(configured),
        n_knots=int(configured.n_knots),
        degree=int(configured.degree),
        knot_strategy=str(configured.knot_strategy),
        penalty=str(configured.penalty),
        select=bool(configured.select),
        knots=None if knots is None else copy.deepcopy(knots),
        discrete=configured.discrete,
        n_bins=configured.n_bins,
        extrapolation=str(configured.extrapolation),
        boundary=None if boundary is None else tuple(float(value) for value in boundary),
        knot_alpha=float(configured.knot_alpha),
        constraint=_constraint(configured),
        m=m,
        lambda_policy=lambda_policy,
    )


def _freeze_categorical(configured: Categorical, fitted: Categorical) -> Categorical:
    grouping = getattr(fitted, "_grouping", None)
    levels = (
        list(grouping.all_original_levels)
        if grouping is not None
        else list(getattr(fitted, "_levels", ()))
    )
    return Categorical(
        base=copy.deepcopy(fitted._base_level),
        grouping=copy.deepcopy(grouping),
        levels=levels,
        unseen=str(configured.unseen),
    )


def _freeze_ordered_categorical(
    configured: OrderedCategorical,
    fitted: OrderedCategorical,
    *,
    term_name: str,
    freeze_geometry: bool,
    freeze_lambdas: bool,
    fitted_lambdas: Mapping[str, float],
) -> OrderedCategorical:
    configured_basis = getattr(configured, "_spline_obj", None)
    fitted_basis = getattr(fitted, "_spline", None)
    if not isinstance(configured_basis, _SplineBase) or not isinstance(fitted_basis, _SplineBase):
        raise MonitoringError(
            f"ordered categorical {term_name!r} must use a spline basis for controlled refits"
        )
    basis = _rebuild_spline(
        configured_basis,
        fitted_basis,
        term_name=term_name,
        freeze_geometry=freeze_geometry,
        freeze_lambdas=freeze_lambdas,
        fitted_lambdas=fitted_lambdas,
    )
    values = copy.deepcopy(
        getattr(fitted, "_original_level_to_value", None)
        or getattr(fitted, "_level_to_value", None)
    )
    if not values:
        raise MonitoringError(
            f"ordered categorical {term_name!r} has no fitted original-level values"
        )
    return OrderedCategorical(
        values=values,
        basis=basis,
        base=copy.deepcopy(fitted._base_level),
        grouping=copy.deepcopy(getattr(fitted, "_grouping", None)),
        specials=copy.deepcopy(getattr(fitted, "_special_raw", None)),
    )


def materialize_monitoring_model(
    baseline_model: SuperGLM,
    variant: MonitoringVariant | str,
) -> SuperGLM:
    """Create an unfitted model obeying one validated monitoring preset."""
    baseline = _require_fitted_superglm(baseline_model)
    resolved_variant = MonitoringVariant(variant)
    if resolved_variant is MonitoringVariant.STATIC_SCORE:
        raise MonitoringError("STATIC_SCORE uses the fitted baseline and has no refit model")

    policy = MONITORING_VARIANT_POLICIES[resolved_variant]
    fitted_lambdas = {
        str(name): float(value)
        for name, value in baseline.reml_diagnostics().get("lambdas", {}).items()
    }
    configured_by_name = dict(baseline._config.feature_templates)
    if set(configured_by_name) != set(baseline._specs):
        raise MonitoringError("SuperGLM configured and fitted feature sets do not match")

    templates: list[tuple[Any, Any]] = []
    for name in baseline._feature_order:
        configured = configured_by_name[name]
        fitted = baseline._specs[name]
        if isinstance(fitted, OrderedCategorical) and isinstance(configured, OrderedCategorical):
            replacement = _freeze_ordered_categorical(
                configured,
                fitted,
                term_name=str(name),
                freeze_geometry=not policy.reposition_data_driven_knots,
                freeze_lambdas=not policy.reestimate_lambdas,
                fitted_lambdas=fitted_lambdas,
            )
        elif isinstance(fitted, Categorical) and isinstance(configured, Categorical):
            replacement = _freeze_categorical(configured, fitted)
        elif isinstance(fitted, _SplineBase) and isinstance(configured, _SplineBase):
            replacement = _rebuild_spline(
                configured,
                fitted,
                term_name=str(name),
                freeze_geometry=not policy.reposition_data_driven_knots,
                freeze_lambdas=not policy.reestimate_lambdas,
                fitted_lambdas=fitted_lambdas,
            )
        elif isinstance(fitted, Polynomial) and isinstance(configured, Polynomial):
            if not policy.reposition_data_driven_knots:
                raise MonitoringError(
                    f"term {name!r} is a data-orthogonal Polynomial whose fitted QR basis "
                    "cannot currently be frozen by SuperGLM; use FULL_ADAPTIVE or replace "
                    "the term with an explicitly governed Spline/Numeric basis"
                )
            replacement = copy.deepcopy(configured)
        elif isinstance(fitted, Numeric) and isinstance(configured, Numeric):
            replacement = copy.deepcopy(configured)
        else:
            raise MonitoringError(
                f"term {name!r} uses unsupported controlled-refit type {type(fitted).__name__}"
            )
        templates.append((name, replacement))

    selected = float(getattr(baseline, "selection_penalty_", 0.0) or 0.0)
    if not math.isclose(selected, 0.0, abs_tol=1e-15):
        raise MonitoringError(
            "controlled REML monitoring requires a baseline with no group-selection "
            "penalty; selection changes are a separate model-spec decision"
        )
    config = baseline._config.with_value(
        feature_templates=tuple(templates),
        features_explicit=True,
        level_bindings=None,
    )
    materialized = config.materialize(type(baseline))
    materialized.selection_penalty = 0.0
    return materialized
