"""Materialize a fresh controlled refit from constructor and fitted metadata."""

from __future__ import annotations

import copy

from superglm import Categorical

from pricing_pipeline.modeling.monitoring.contracts import MonitoringError, MonitoringVariant
from pricing_pipeline.modeling.recipes.superglm import decode_estimator


def materialize(payload, variant):
    variant = MonitoringVariant(variant)
    if variant is MonitoringVariant.STATIC_SCORE:
        raise MonitoringError("STATIC_SCORE uses the saved predictor and has no refit model")
    recipe = copy.deepcopy(payload["recipe"])
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
