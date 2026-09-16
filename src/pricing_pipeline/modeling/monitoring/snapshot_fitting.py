"""Materialize a fresh controlled refit from constructor and fitted metadata."""

from __future__ import annotations

import copy

from superglm import Categorical

from pricing_pipeline.modeling.monitoring.contracts import (
    MonitoringError,
    MonitoringLambda,
    MonitoringVariant,
)
from pricing_pipeline.modeling.recipes.superglm import decode_estimator

SPLINE_CONTROL_FIELDS = frozenset({"knots", "boundary", "lambda_policy"})


def spline_recipes(recipe):
    """Select the constructor controls shared by continuous and ordered splines."""
    return {
        name: feature["basis"] if feature["type"] == "OrderedCategorical" else feature
        for name, feature in recipe["features"].items()
        if feature["type"] in {"Spline", "OrderedCategorical"}
    }


def declared_monitoring_policy(payload):
    """Return independent declared controls, deriving them for original v1 snapshots."""
    if "declared_monitoring_policy" in payload:
        return copy.deepcopy(payload["declared_monitoring_policy"])
    return {
        "schema_version": 1,
        "splines": {
            name: {key: copy.deepcopy(feature[key]) for key in SPLINE_CONTROL_FIELDS}
            for name, feature in spline_recipes(payload["recipe"]).items()
        },
    }


def monitoring_recipe(payload):
    """Restore declared controls without changing the saved execution constructor."""
    recipe = copy.deepcopy(payload["recipe"])
    policy = declared_monitoring_policy(payload)
    for name, spline in spline_recipes(recipe).items():
        spline.update(copy.deepcopy(policy["splines"][name]))
    return recipe


def declared_geometry_fields(payload):
    policy = declared_monitoring_policy(payload)
    return tuple(
        sorted(
            f"{name}.{field}"
            for name, controls in policy["splines"].items()
            for field in ("knots", "boundary")
            if controls[field] is not None
        )
    )


def declared_lambda_policies(payload):
    """Combine this fitted model's lambda values with inherited declared modes."""
    controls = declared_monitoring_policy(payload)["splines"]
    raw = payload["fit_contract"]["fitted_lambdas"]
    order = payload["recipe"]["feature_order"]
    component_terms = {}
    for component in raw:
        candidates = [
            name for name in order if component == name or component.startswith(name + ":")
        ]
        component_terms[component] = max(candidates, key=len) if candidates else None
    rows = []
    for component, value in sorted(raw.items()):
        name = component_terms[component]
        single_component = name is not None and list(component_terms.values()).count(name) == 1
        canonical = (
            name if single_component and component in {name, name + ":wiggle"} else component
        )
        policy = controls.get(name, {}).get("lambda_policy")
        if policy is not None and "mode" not in policy:
            suffix = component.removeprefix(name + ":")
            if suffix == name and single_component:
                suffix = "wiggle"
            policy = policy.get(suffix)
        mode = "FIXED" if policy is not None and policy.get("mode") == "fixed" else "ESTIMATED"
        rows.append(MonitoringLambda(name, canonical, float(value), mode))
    return tuple(rows)


def materialize(payload, variant):
    variant = MonitoringVariant(variant)
    if variant is MonitoringVariant.STATIC_SCORE:
        raise MonitoringError("STATIC_SCORE uses the saved predictor and has no refit model")
    recipe = monitoring_recipe(payload)
    # A profiled family parameter belongs to the fitted baseline being monitored.
    recipe["estimator"]["family"] = copy.deepcopy(payload["prediction"]["family"])
    recipe["estimator"]["link"] = copy.deepcopy(payload["prediction"]["link"])
    terms = {
        item["source_term_name"]: item for item in payload["receipt"]["term_metadata"].values()
    }
    lambdas = payload["fit_contract"]["fitted_lambdas"]
    for name, feature in recipe["features"].items():
        metadata = terms[name]
        if feature["type"] == "OrderedCategorical":
            feature["base"] = metadata["fitted"]["base_level"]
        if feature["type"] == "OrderedCategorical":
            spline, spline_metadata = feature["basis"], metadata["spline"]
        elif feature["type"] == "Spline":
            spline, spline_metadata = feature, metadata
        else:
            continue
        if variant is not MonitoringVariant.FULL_ADAPTIVE:
            spline["knots"] = spline_metadata["fitted"]["knots"]
            spline["boundary"] = spline_metadata["fitted"]["boundary"]
        if variant is MonitoringVariant.FROZEN_REFIT:
            if name in lambdas:
                spline["lambda_policy"] = {"mode": "fixed", "value": lambdas[name]}
            else:
                components = {
                    key.removeprefix(name + ":"): {"mode": "fixed", "value": value}
                    for key, value in lambdas.items()
                    if key.startswith(name + ":")
                }
                if components:
                    spline["lambda_policy"] = components
                elif "lambda2" in lambdas:
                    spline["lambda_policy"] = {"mode": "fixed", "value": lambdas["lambda2"]}
    model = decode_estimator(
        recipe["estimator"], recipe["features"], recipe["feature_order"], recipe["interactions"]
    )
    templates = []
    for name, configured in model._config.feature_templates:
        if isinstance(configured, Categorical):
            # Captured fitted domains can distinguish 1 from "1". Preserve that
            # native constructor contract without weakening editable recipe labels.
            grouping = copy.deepcopy(configured._grouping)
            levels = (
                list(grouping.all_original_levels)
                if grouping is not None
                else copy.deepcopy(terms[name]["fitted"]["levels"])
            )
            configured = Categorical(
                base=copy.deepcopy(terms[name]["fitted"]["base_level"]),
                grouping=grouping,
                levels=levels,
                unseen=configured.unseen,
            )
        templates.append((name, configured))
    model = model._config.with_value(
        feature_templates=tuple(templates), features_explicit=True, level_bindings=None
    ).materialize(type(model))
    model.selection_penalty = 0.0
    return model
