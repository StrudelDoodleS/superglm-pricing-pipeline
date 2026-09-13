"""Extract monitoring terms, smoothing parameters, relativities and loss metrics.

Return immutable records for MonitoringFitResult and compute its canonical digest.
No database writes happen during extraction."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd
from superglm import SuperGLM
from superglm.features.ordered_categorical import OrderedCategorical
from superglm.types import LambdaPolicy

from pricing_pipeline.modeling.monitoring.contracts import (
    RESULT_EVIDENCE_SCHEMA,
    RESULT_EVIDENCE_SCHEMA_VERSION,
    MonitoringError,
    MonitoringFitResult,
    MonitoringLambda,
    MonitoringRelativity,
    MonitoringTerm,
    MonitoringVariant,
    _canonical_json,
    _categorical_scalar_identity,
    _label_point_key,
    _sha256_text,
)
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
    build_superglm_publication_receipt,
)


def _monitoring_fit_configuration_json(
    *,
    variant: MonitoringVariant,
    baseline_identity: Mapping[str, Any] | None,
    model_frame_sha256: str | None,
    target_column: str | None,
    fit_sample_weight_name: str | None,
    offset_column: str | None,
    offset_contract: OffsetExportContract,
    continuous_points: int,
    max_reml_iter: int,
    reml_tol: float | None,
    runtime_validation: str | bool,
) -> str:
    refits = variant is not MonitoringVariant.STATIC_SCORE
    return _canonical_json(
        {
            "schema_name": "superglm_monitoring_fit_configuration",
            "schema_version": 1,
            "variant": variant.value,
            "baseline": baseline_identity,
            "model_frame_sha256": model_frame_sha256,
            "target_column": target_column,
            "fit_sample_weight_name": fit_sample_weight_name,
            "offset_column": offset_column,
            "offset_contract": offset_contract.model_dump(mode="json"),
            "continuous_points": continuous_points,
            "max_reml_iter": max_reml_iter if refits else None,
            "reml_tol": reml_tol if refits else None,
            "runtime_validation": runtime_validation if refits else None,
        }
    )


def _monitoring_result_evidence_sha256(result: MonitoringFitResult) -> str:
    payload = {
        "schema_name": RESULT_EVIDENCE_SCHEMA,
        "schema_version": RESULT_EVIDENCE_SCHEMA_VERSION,
        "variant": result.variant.value,
        "contract_sha256": result.contract.contract_sha256,
        "model_frame_sha256": result.model_frame_sha256,
        "fit_configuration": json.loads(result.fit_configuration_json),
        "terms": [
            {
                "term_name": row.term_name,
                "term_kind": row.term_kind,
                "sequence_no": row.sequence_no,
                "metadata_json": json.loads(row.metadata_json),
                "structure_sha256": row.structure_sha256,
            }
            for row in result.terms
        ],
        "lambdas": [
            {
                "term_name": row.term_name,
                "component_name": row.component_name,
                "lambda_value": row.lambda_value,
                "lambda_mode": row.lambda_mode,
            }
            for row in result.lambdas
        ],
        "relativities": [
            {
                "term_name": row.term_name,
                "term_kind": row.term_kind,
                "point_key": row.point_key,
                "point_label": row.point_label,
                "point_numeric": row.point_numeric,
                "relativity": row.relativity,
                "log_relativity": row.log_relativity,
                "is_reference": row.is_reference,
            }
            for row in result.relativities
        ],
        "metrics": dict(result.metrics),
        "invariant_evidence_sha256": result.invariant_evidence.evidence_sha256,
    }
    return _sha256_text(_canonical_json(payload))


def _result_terms(
    model: SuperGLM,
    *,
    offset_contract: OffsetExportContract,
    fit_sample_weight_name: str | None,
    export_weight_name: str | None,
) -> tuple[MonitoringTerm, ...]:
    receipt = build_superglm_publication_receipt(
        model,
        offset_contract=offset_contract,
        fit_sample_weight_name=fit_sample_weight_name,
        export_weight_name=export_weight_name,
    )
    terms: list[MonitoringTerm] = []
    for sequence_no, metadata in enumerate(receipt.term_metadata.values(), start=1):
        metadata_json = _canonical_json(metadata)
        terms.append(
            MonitoringTerm(
                term_name=str(metadata["source_term_name"]),
                term_kind=str(metadata["feature_kind"]),
                sequence_no=sequence_no,
                metadata_json=metadata_json,
                structure_sha256=_sha256_text(metadata_json),
            )
        )
    return tuple(terms)


def _lambda_term(component_name: str, term_names: tuple[str, ...]) -> str | None:
    matches = [
        term_name
        for term_name in term_names
        if component_name == term_name or component_name.startswith(f"{term_name}:")
    ]
    return max(matches, key=len) if matches else None


def _component_policy(model: SuperGLM, term_name: str | None, component: str) -> Any:
    if term_name is None:
        return None
    spec = model._specs.get(term_name)
    if isinstance(spec, OrderedCategorical):
        spec = getattr(spec, "_spline", None)
    policy = getattr(spec, "_lambda_policy", None)
    if isinstance(policy, Mapping):
        suffix = component.removeprefix(f"{term_name}:")
        return policy.get(suffix)
    return policy


def _canonical_component_names(
    model: SuperGLM,
    raw: Mapping[str, Any],
) -> dict[str, str]:
    term_names = tuple(str(name) for name in model._feature_order)
    component_terms = {
        str(component): _lambda_term(str(component), term_names) for component in raw
    }
    canonical: dict[str, str] = {}
    for component in raw:
        raw_component = str(component)
        term_name = component_terms[raw_component]
        sibling_count = sum(sibling_term == term_name for sibling_term in component_terms.values())
        # SuperGLM names a lone estimated component ``term`` but the same
        # component ``term:wiggle`` when LambdaPolicy.fixed is explicit.  One
        # canonical name keeps week-to-week joins stable; multi-component
        # terms retain their meaningful suffixes.
        canonical[raw_component] = (
            term_name
            if term_name is not None
            and sibling_count == 1
            and raw_component in {term_name, f"{term_name}:wiggle"}
            else raw_component
        )
    if len(set(canonical.values())) != len(canonical):
        raise MonitoringError("SuperGLM returned ambiguous canonical lambda component names")
    return canonical


def _canonical_lambda_values(
    model: SuperGLM,
    raw: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    resolved = model.reml_diagnostics().get("lambdas", {}) if raw is None else raw
    names = _canonical_component_names(model, resolved)
    return {
        names[str(component)]: float(value)
        for component, value in sorted(resolved.items(), key=lambda item: str(item[0]))
    }


def _result_lambdas(
    model: SuperGLM,
    variant: MonitoringVariant,
) -> tuple[MonitoringLambda, ...]:
    raw = model.reml_diagnostics().get("lambdas", {})
    term_names = tuple(str(name) for name in model._feature_order)
    component_terms = {
        str(component): _lambda_term(str(component), term_names) for component in raw
    }
    canonical_names = _canonical_component_names(model, raw)
    rows: list[MonitoringLambda] = []
    for component, value in sorted(raw.items()):
        raw_component = str(component)
        term_name = component_terms[raw_component]
        component_name = canonical_names[raw_component]
        if variant is MonitoringVariant.STATIC_SCORE:
            mode = "BASELINE"
        elif variant is MonitoringVariant.FROZEN_REFIT:
            mode = "FIXED"
        else:
            component_policy = _component_policy(model, term_name, raw_component)
            mode = (
                "FIXED"
                if isinstance(component_policy, LambdaPolicy) and component_policy.mode == "fixed"
                else "ESTIMATED"
            )
        rows.append(
            MonitoringLambda(
                term_name=term_name,
                component_name=component_name,
                lambda_value=float(value),
                lambda_mode=mode,
            )
        )
    return tuple(rows)


def _requested_level_values(
    inference: Any,
    points: list[Any],
) -> list[tuple[Any, float, float]]:
    levels = list(inference.levels or [])
    by_identity: dict[str, int] = {}
    for index, level in enumerate(levels):
        identity = _canonical_json(_categorical_scalar_identity(level))
        if identity in by_identity:
            raise MonitoringError(
                "fitted categorical levels have an ambiguous typed canonical identity"
            )
        by_identity[identity] = index
    rows: list[tuple[Any, float, float]] = []
    requested_identities: set[str] = set()
    for point in points:
        if (
            not isinstance(point, Mapping)
            or set(point) != {"identity", "label"}
            or not isinstance(point["identity"], Mapping)
            or not isinstance(point["label"], str)
        ):
            raise MonitoringError("frozen categorical grid point is malformed")
        identity = _canonical_json(point["identity"])
        if identity in requested_identities:
            raise MonitoringError(
                "frozen categorical grid has an ambiguous typed canonical identity"
            )
        requested_identities.add(identity)
        index = by_identity.get(identity)
        if index is None:
            raise MonitoringError(f"controlled refit is missing frozen categorical level {point!r}")
        rows.append(
            (
                point,
                float(np.asarray(inference.relativity)[index]),
                float(np.asarray(inference.log_relativity)[index]),
            )
        )
    return rows


def _requested_continuous_values(
    model: SuperGLM,
    term_name: str,
    points: list[Any],
) -> list[tuple[Any, float, float]]:
    requested_x = np.asarray(points, dtype=float)
    if requested_x.ndim != 1 or not np.isfinite(requested_x).all():
        raise MonitoringError(f"term {term_name!r} has an invalid frozen numeric grid")
    spec = model._specs.get(term_name)
    feature_groups = [group for group in model._groups if group.feature_name == term_name]
    if spec is None or not feature_groups:
        raise MonitoringError(f"term {term_name!r} has no fitted continuous contribution")
    beta_combined = np.concatenate(
        [np.asarray(model.result.beta[group.sl], dtype=float).ravel() for group in feature_groups]
    )
    transformed = np.asarray(spec.transform(requested_x), dtype=float)
    expected_shape = (len(requested_x), len(beta_combined))
    if transformed.shape != expected_shape:
        raise MonitoringError(
            f"term {term_name!r} transform returned {transformed.shape}, expected {expected_shape}"
        )
    if not np.isfinite(beta_combined).all() or not np.isfinite(transformed).all():
        raise MonitoringError(f"term {term_name!r} continuous contribution is not finite")
    requested_log = transformed @ beta_combined
    with np.errstate(over="ignore", invalid="ignore"):
        requested_relativity = np.exp(requested_log)
    if not np.isfinite(requested_log).all() or not np.isfinite(requested_relativity).all():
        raise MonitoringError(f"term {term_name!r} continuous relativity is not finite")
    return [
        (point, float(relativity), float(log_relativity))
        for point, relativity, log_relativity in zip(
            points,
            requested_relativity,
            requested_log,
            strict=True,
        )
    ]


def _result_relativities(
    model: SuperGLM,
    evaluation_grid: Mapping[str, Mapping[str, Any]],
) -> tuple[MonitoringRelativity, ...]:
    rows: list[MonitoringRelativity] = []
    generic_frames = model.relativities(with_se=False, centering="native")
    for term_name, grid in evaluation_grid.items():
        kind = str(grid["kind"])
        points = list(grid["points"])
        if kind == "categorical_interaction":
            frame = generic_frames.get(term_name)
            if frame is None or "level" not in frame:
                raise MonitoringError(f"interaction {term_name!r} has no comparable levels")
            indexed = frame.assign(_key=frame["level"].astype(str)).set_index("_key")
            values = []
            for point in points:
                if str(point) not in indexed.index:
                    raise MonitoringError(
                        f"interaction {term_name!r} is missing frozen point {point!r}"
                    )
                record = indexed.loc[str(point)]
                values.append((point, float(record["relativity"]), float(record["log_relativity"])))
        elif kind == "continuous":
            values = _requested_continuous_values(model, term_name, points)
        else:
            inference = model.term_inference(
                term_name,
                with_se=False,
                n_points=max(501, len(points)),
                centering="native",
            )
            if kind == "categorical":
                values = _requested_level_values(inference, points)
            elif kind == "numeric":
                values = [
                    (
                        "per_unit",
                        float(np.asarray(inference.relativity).ravel()[0]),
                        float(np.asarray(inference.log_relativity).ravel()[0]),
                    )
                ]
            else:
                raise MonitoringError(f"unsupported evaluation-grid kind {kind!r}")

        for point, relativity, log_relativity in values:
            point_numeric = float(point) if kind == "continuous" else None
            if kind == "categorical":
                point_label = str(point["label"])
                point_key = _label_point_key({"level": point["identity"]})
            else:
                point_label = None if point_numeric is not None else str(point)
                if point_numeric is not None:
                    point_key = _canonical_json({"x": point_numeric})
                elif kind == "numeric":
                    point_key = _canonical_json({"level": point})
                else:
                    point_key = _label_point_key({"level": point})
            rows.append(
                MonitoringRelativity(
                    term_name=term_name,
                    term_kind=kind,
                    point_key=point_key,
                    point_label=point_label,
                    point_numeric=point_numeric,
                    relativity=relativity,
                    log_relativity=log_relativity,
                    is_reference=math.isclose(log_relativity, 0.0, abs_tol=1e-12),
                )
            )
    return tuple(rows)


def _result_metrics(
    model: SuperGLM,
    X: pd.DataFrame,
    y: Any,
    sample_weight: Any,
    offset: Any,
) -> Mapping[str, float]:
    predictions = np.asarray(model.predict(X, offset=offset), dtype=float)
    observed = np.asarray(y, dtype=float)
    diagnostics = model.metrics(X, observed, sample_weight, offset)
    weights = (
        np.ones(len(X), dtype=float)
        if sample_weight is None
        else np.asarray(sample_weight, dtype=float)
    )
    weight_sum = float(np.sum(weights))
    weighted_observed_sum = float(np.dot(weights, observed))
    weighted_prediction_sum = float(np.dot(weights, predictions))
    metrics = {
        "row_count": float(len(X)),
        "sample_weight_sum": weight_sum,
        "sample_weighted_mean_observed": weighted_observed_sum / weight_sum,
        "sample_weighted_mean_prediction": weighted_prediction_sum / weight_sum,
        "sample_weighted_sum_observed": weighted_observed_sum,
        "sample_weighted_sum_prediction": weighted_prediction_sum,
    }
    for name in ("deviance", "null_deviance", "explained_deviance", "log_likelihood"):
        value = getattr(diagnostics, name, None)
        if value is not None and np.isscalar(value) and math.isfinite(float(value)):
            metrics[name] = float(value)
    return MappingProxyType(dict(sorted(metrics.items())))
