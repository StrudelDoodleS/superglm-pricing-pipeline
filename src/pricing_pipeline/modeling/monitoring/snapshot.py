"""Versioned SQL monitoring baselines with explicit configuration and scoring data.

Only constructor settings, fitted term geometry, exact additive predictors and
aggregate reference counts cross this boundary. No fitted object or source row
is serialized or reconstructed.
"""

from __future__ import annotations

import json
import math
import platform
from dataclasses import asdict, dataclass
from importlib.metadata import version
from typing import Any

import numpy as np
from superglm import Categorical, Numeric, OrderedCategorical
from superglm.export._ppform import PpformNotExactError, extract_ppform
from superglm.features.spline import _SplineBase

from pricing_pipeline.modeling.monitoring import snapshot_fitting, snapshot_prediction
from pricing_pipeline.modeling.monitoring.contracts import (
    ModelFitContract,
    MonitoringError,
    MonitoringLambda,
    MonitoringTerm,
    MonitoringVariant,
    _canonical_json,
    _categorical_scalar_identity,
    _required_sha256,
    _sha256_text,
)
from pricing_pipeline.modeling.recipes.schema import RecipeError, UnsupportedRecipeError
from pricing_pipeline.modeling.recipes.superglm import (
    encode_estimator,
    encode_object,
)
from pricing_pipeline.publishing.metadata import OffsetExportContract

SNAPSHOT_SCHEMA = "superglm_monitoring_snapshot"
SNAPSHOT_SCHEMA_VERSION = 1


class MonitoringSnapshotUnsupported(MonitoringError):
    """The model uses a feature outside the governed SQL snapshot coverage."""


@dataclass(frozen=True)
class MonitoringSnapshot:
    snapshot_json: str
    snapshot_sha256: str
    schema_version: int
    superglm_version: str


@dataclass(frozen=True)
class SqlBaseline:
    snapshot_json: str
    snapshot_sha256: str
    identity: dict[str, Any] | None = None

    @property
    def model_run_id(self):
        if self.identity is None or self.identity.get("model_run_id") is None:
            raise MonitoringError("SQL baseline has no bound model run identity")
        return self.identity["model_run_id"]

    @property
    def deployment_id(self):
        if self.identity is None or self.identity.get("deployment_id") is None:
            raise MonitoringError("SQL baseline has no bound deployment identity")
        return self.identity["deployment_id"]

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(self.payload()["recipe"]["feature_order"])

    def payload(self) -> dict[str, Any]:
        return json.loads(self.snapshot_json)

    @property
    def offset_contract(self) -> OffsetExportContract:
        return OffsetExportContract.model_validate(self.payload()["receipt"]["offset_contract"])

    @property
    def fit_sample_weight_name(self) -> str | None:
        return self.payload()["fit_sample_weight_name"]

    @property
    def export_weight_name(self) -> str | None:
        return self.payload()["export_weight_name"]

    @property
    def input_transforms(self) -> dict[str, Any] | None:
        return self.payload()["input_transforms"]

    @property
    def terms(self) -> tuple[MonitoringTerm, ...]:
        return tuple(MonitoringTerm(**item) for item in self.payload()["terms"])

    @property
    def term_metadata(self) -> dict[str, Any]:
        return {
            item["source_term_name"]: item
            for item in self.payload()["receipt"]["term_metadata"].values()
        }

    @property
    def lambdas(self) -> tuple[MonitoringLambda, ...]:
        return tuple(MonitoringLambda(**item) for item in self.payload()["lambdas"])

    def model_fit_contract(self, continuous_points: int = 101) -> ModelFitContract:
        if (
            isinstance(continuous_points, bool)
            or not isinstance(continuous_points, int)
            or continuous_points < 2
        ):
            raise ValueError("continuous_points must be at least 2")
        contract = self.payload()["fit_contract"]
        for grid in contract["evaluation_grid"].values():
            if grid["kind"] == "continuous":
                points = grid["points"]
                grid["points"] = np.linspace(points[0], points[-1], continuous_points).tolist()
        encoded = _canonical_json(contract)
        return ModelFitContract(
            encoded,
            _sha256_text(encoded),
            contract["structure_sha256"],
            contract["superglm_version"],
        )

    def materialize(self, variant):
        return snapshot_fitting.materialize(self.payload(), variant)

    def predict(self, X, offset=None):
        return snapshot_prediction.predict(self.payload(), X, offset)

    def metrics(self, X, y, sample_weight=None, offset=None):
        return snapshot_prediction.metrics(self.payload(), X, y, sample_weight, offset)

    def relativities(self, evaluation_grid):
        return snapshot_prediction.relativities(self.payload(), evaluation_grid)


def _term_beta(model, name):
    groups = [group for group in model._groups if group.feature_name == name]
    return (
        np.concatenate([np.asarray(model.result.beta[group.sl], dtype=float) for group in groups])
        if groups
        else np.empty(0)
    )


def _capture_prediction(model):
    from pricing_pipeline.modeling.monitoring.data_checks import _categorical_domain

    terms = {}
    for name in model._feature_order:
        spec, beta = model._specs[name], _term_beta(model, name)
        if isinstance(spec, (Categorical, OrderedCategorical)):
            ordered = isinstance(spec, OrderedCategorical)
            if ordered and not isinstance(spec._spline_obj, _SplineBase):
                raise MonitoringSnapshotUnsupported(
                    f"ordered term {name!r} uses unsupported snapshot basis "
                    f"{type(spec._spline_obj).__name__}"
                )
            allowed, _ = _categorical_domain(spec, np.asarray([], dtype=object))
            if ordered and spec._grouping is not None:
                # Native ordered scoring accepts known group labels too.
                allowed = list(dict.fromkeys([*allowed, *spec._grouping.grouped_levels]))
            raw = np.asarray(allowed, dtype=object)
            effects = np.asarray(spec.score(raw, beta), dtype=float)
            inference = model.term_inference(name, with_se=False, centering="native")
            terms[name] = {
                "kind": "ordered_categorical" if ordered else "categorical",
                "string_inputs": spec._grouping is not None,
                "unseen": "error" if ordered or spec._grouping is not None else spec.unseen,
                "canonical_levels": [
                    _categorical_scalar_identity(value)
                    for value in (
                        (
                            [*spec._grouping.all_original_levels, *spec._ordered_levels]
                            if spec._grouping is not None
                            else spec._ordered_levels
                        )
                        if ordered
                        else []
                    )
                ],
                "levels": [
                    {
                        "identity": _categorical_scalar_identity(value),
                        "label": str(value),
                        "log_effect": float(effect),
                    }
                    for value, effect in zip(allowed, effects, strict=True)
                ],
                "report_levels": [
                    {
                        "identity": _categorical_scalar_identity(value),
                        "label": str(value),
                        "log_relativity": float(effect),
                    }
                    for value, effect in zip(
                        inference.levels, inference.log_relativity, strict=True
                    )
                ],
            }
        elif type(spec) is Numeric:
            terms[name] = {
                "kind": "numeric",
                "coefficient": float(spec.score(np.asarray([1.0]), beta)[0]),
            }
        elif isinstance(spec, _SplineBase):
            pieces = extract_ppform(model, name, centering="native")
            term = {
                "kind": "spline",
                "breaks": pieces.breaks.tolist(),
                "coefficients": pieces.coefficients.tolist(),
                "degree": pieces.degree,
                "extrapolation": pieces.extrapolation,
                "left_tail": None,
                "right_tail": None,
            }
            if pieces.extrapolation == "extend":
                from pricing_pipeline.publishing.metadata import _spline_kind

                span = pieces.breaks[-1] - pieces.breaks[0]
                left, right = pieces.coefficients[0], pieces.coefficients[-1]
                left_scale = span / (pieces.breaks[1] - pieces.breaks[0])
                right_scale = span / (pieces.breaks[-1] - pieces.breaks[-2])
                # Taylor coefficients at each boundary, expressed in z=(x-boundary)/span.
                left_tail = left * left_scale ** np.arange(4)
                right_tail = np.asarray(
                    [
                        np.sum(right),
                        right[1] + 2 * right[2] + 3 * right[3],
                        right[2] + 3 * right[3],
                        right[3],
                    ]
                ) * right_scale ** np.arange(4)
                kind = _spline_kind(spec)
                if kind in {"cr", "cr_cardinal"} or (kind == "ns" and pieces.degree >= 3):
                    left_tail[2:] = 0.0
                    right_tail[2:] = 0.0
                term["left_tail"], term["right_tail"] = left_tail.tolist(), right_tail.tolist()
            terms[name] = term
        else:
            raise MonitoringSnapshotUnsupported(
                f"term {name!r} uses unsupported SQL snapshot type {type(spec).__name__}"
            )
    return {
        "intercept": float(model.result.intercept),
        "phi": float(model.result.phi),
        "family": encode_object(model._distribution, "family", "snapshot.family"),
        "link": encode_object(model._link, "link", "snapshot.link"),
        "weight_semantics": model._config.weight_semantics,
        "terms": terms,
    }


def capture_monitoring_snapshot(bundle) -> MonitoringSnapshot:
    from pricing_pipeline.modeling.monitoring.baseline import _require_fitted_superglm
    from pricing_pipeline.modeling.monitoring.data_checks import _inspect_features
    from pricing_pipeline.modeling.monitoring.evidence import _result_lambdas, _result_terms
    from pricing_pipeline.modeling.monitoring.fitting import build_model_fit_contract
    from pricing_pipeline.modeling.monitoring.invariants import (
        _geometry_from_receipt,
        _normalized_runtime_structure,
        _protected_geometry_fields,
    )
    from pricing_pipeline.publishing.metadata import build_superglm_publication_receipt

    model = _require_fitted_superglm(bundle.fitted_model)
    if (
        model._interaction_order
        or model._config.interactions
        or model._config.interaction_templates
    ):
        raise MonitoringSnapshotUnsupported("SQL monitoring snapshots do not support interactions")
    if not math.isclose(float(model.selection_penalty_ or 0.0), 0.0, abs_tol=1e-15):
        raise MonitoringSnapshotUnsupported(
            "SQL monitoring snapshots require zero group-selection penalty"
        )
    try:
        estimator, features, interactions = encode_estimator(model)
        prediction = _capture_prediction(model)
    except (UnsupportedRecipeError, PpformNotExactError) as exc:
        raise MonitoringSnapshotUnsupported(str(exc)) from exc
    kwargs = {
        "offset_contract": bundle.offset_contract,
        "fit_sample_weight_name": bundle.fit_sample_weight_name,
        "export_weight_name": bundle.export_weight_name,
    }
    preparation = getattr(bundle, "input_transforms", None)
    receipt = build_superglm_publication_receipt(
        model, **kwargs, input_transforms=preparation
    ).model_dump(mode="json")
    contract = build_model_fit_contract(model, **kwargs, input_transforms=preparation)
    reference_issues, reference_profiles = _inspect_features(model, bundle.X, bundle.sample_weight)
    if any(item["severity"] == "error" for item in reference_issues):
        raise MonitoringError("cannot capture SQL monitoring reference from incompatible inputs")
    payload = {
        "schema_name": SNAPSHOT_SCHEMA,
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "python_version": platform.python_version(),
        "superglm_version": version("superglm"),
        "recipe": {
            "estimator": estimator,
            "features": features,
            "feature_order": list(model._feature_order),
            "interactions": interactions,
        },
        "receipt": receipt,
        "telemetry": model.training_telemetry(),
        "fit_contract": contract.payload(),
        "normalized_structure": _normalized_runtime_structure(model, receipt),
        "protected_geometry_fields": list(
            _protected_geometry_fields(
                model, MonitoringVariant.FULL_ADAPTIVE, _geometry_from_receipt(receipt)
            )
        ),
        "terms": [asdict(item) for item in _result_terms(model, **kwargs)],
        "lambdas": [
            asdict(item) for item in _result_lambdas(model, MonitoringVariant.STATIC_SCORE)
        ],
        "fitted_lambda_policies": [
            asdict(item) for item in _result_lambdas(model, MonitoringVariant.REESTIMATE_LAMBDA)
        ],
        "prediction": prediction,
        "reference_profiles": reference_profiles,
        "reference_has_weights": bundle.sample_weight is not None,
        "reml_termination_reason": model.reml_diagnostics().get("termination_reason"),
        "bundle_identity": {
            key: getattr(bundle, key)
            for key in (
                "model_name",
                "model_version",
                "export_id",
                "manifest_id",
                "split_set_id",
                "row_order_sha256",
                "model_source_sha256",
                "model_frame_sha256",
            )
        },
        "input_transforms": preparation,
        "fit_sample_weight_name": bundle.fit_sample_weight_name,
        "export_weight_name": bundle.export_weight_name,
    }
    encoded = _canonical_json(payload)
    digest = _sha256_text(encoded)
    restored = restore_monitoring_snapshot(encoded, expected_sha256=digest)
    # Validate actual fit rows transiently; these predictions are never serialized.
    actual = restored.predict(bundle.X)
    expected = model.predict(bundle.X)
    if not np.allclose(actual, expected, rtol=1e-10, atol=1e-11):
        raise MonitoringError("explicit SQL predictor does not reproduce the fitted model")
    offset = getattr(bundle, "offset", None)
    if offset is not None and not np.allclose(
        restored.predict(bundle.X, offset), model.predict(bundle.X, offset), rtol=1e-10, atol=1e-11
    ):
        raise MonitoringError("explicit SQL predictor does not reproduce fitted model offsets")
    return MonitoringSnapshot(encoded, digest, SNAPSHOT_SCHEMA_VERSION, payload["superglm_version"])


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MonitoringError(f"duplicate snapshot field {key!r}")
        result[key] = value
    return result


def restore_monitoring_snapshot(snapshot_json: str, *, expected_sha256: str) -> SqlBaseline:
    from pricing_pipeline.modeling.monitoring.snapshot_validation import validate_snapshot_payload

    _required_sha256(expected_sha256, "snapshot digest")
    if not isinstance(snapshot_json, str) or _sha256_text(snapshot_json) != expected_sha256:
        raise MonitoringError("SQL monitoring snapshot digest mismatch")
    try:
        payload = json.loads(
            snapshot_json,
            object_pairs_hook=_object_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON {value}")
            ),
        )
        if _canonical_json(payload) != snapshot_json:
            raise MonitoringError("SQL monitoring snapshot JSON must be canonical")
        validate_snapshot_payload(payload)
    except MonitoringError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecipeError) as exc:
        raise MonitoringError(f"invalid SQL monitoring snapshot: {exc}") from exc
    return SqlBaseline(snapshot_json, expected_sha256)
