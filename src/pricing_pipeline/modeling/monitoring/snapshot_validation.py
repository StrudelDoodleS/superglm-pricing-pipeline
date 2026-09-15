"""Validate SQL snapshot schemas and the consistency of their saved evidence."""

from __future__ import annotations

import json
import math
import platform
from dataclasses import asdict
from importlib.metadata import version

import numpy as np

from pricing_pipeline.modeling.monitoring import snapshot_prediction
from pricing_pipeline.modeling.monitoring.contracts import (
    MonitoringError,
    MonitoringLambda,
    MonitoringTerm,
    _canonical_json,
    _sha256_text,
)
from pricing_pipeline.modeling.recipes.schema import RecipeError
from pricing_pipeline.modeling.recipes.superglm import decode_estimator, decode_object
from pricing_pipeline.publishing.metadata import SuperGLMPublicationReceipt

_FIELDS = frozenset(
    {
        "schema_name",
        "schema_version",
        "python_version",
        "superglm_version",
        "recipe",
        "receipt",
        "telemetry",
        "fit_contract",
        "normalized_structure",
        "protected_geometry_fields",
        "terms",
        "lambdas",
        "prediction",
        "reference_profiles",
        "reference_has_weights",
        "bundle_identity",
        "input_transforms",
        "fit_sample_weight_name",
        "export_weight_name",
        "reml_termination_reason",
        "fitted_lambda_policies",
    }
)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_snapshot_payload(payload):
    from pricing_pipeline.modeling.monitoring.snapshot import (
        SNAPSHOT_SCHEMA,
        SNAPSHOT_SCHEMA_VERSION,
    )

    if not isinstance(payload, dict):
        raise MonitoringError("invalid SQL monitoring snapshot fields")
    if (
        payload["schema_name"] != SNAPSHOT_SCHEMA
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] not in {1, SNAPSHOT_SCHEMA_VERSION}
    ):
        raise MonitoringError("unsupported SQL monitoring snapshot schema")
    expected_fields = _FIELDS | (
        {"declared_monitoring_policy"} if payload["schema_version"] == 2 else set()
    )
    if set(payload) != expected_fields:
        raise MonitoringError("invalid SQL monitoring snapshot fields")
    if payload["superglm_version"] != version("superglm"):
        raise MonitoringError(
            "SQL monitoring snapshot SuperGLM version does not match this runtime"
        )
    if str(payload["python_version"]).split(".")[:2] != platform.python_version().split(".")[:2]:
        raise MonitoringError(
            "SQL monitoring snapshot Python major/minor does not match this runtime"
        )
    recipe = payload["recipe"]
    if (
        not isinstance(recipe, dict)
        or set(recipe) != {"estimator", "features", "feature_order", "interactions"}
        or recipe["interactions"]
    ):
        raise MonitoringError("unsupported SQL monitoring snapshot recipe")
    order = recipe["feature_order"]
    if (
        not isinstance(order, list)
        or not order
        or any(not isinstance(name, str) for name in order)
        or len(set(order)) != len(order)
        or set(order) != set(recipe["features"])
    ):
        raise MonitoringError("invalid snapshot feature order")
    decode_estimator(recipe["estimator"], recipe["features"], order, [])
    receipt = SuperGLMPublicationReceipt.model_validate(payload["receipt"])
    if {
        item["source_term_name"]
        for item in receipt.term_metadata.values()
        if item["feature_kind"] != "offset"
    } != set(order):
        raise MonitoringError("snapshot recipe and receipt features differ")
    prediction = payload["prediction"]
    if set(prediction) != {
        "intercept",
        "phi",
        "family",
        "link",
        "weight_semantics",
        "terms",
    } or set(prediction["terms"]) != set(order):
        raise MonitoringError("invalid snapshot predictor fields")
    if (
        not _finite(prediction["intercept"])
        or not _finite(prediction["phi"])
        or prediction["phi"] <= 0
        or prediction["weight_semantics"] not in {"prior", "frequency"}
    ):
        raise MonitoringError("invalid snapshot fitted family settings")
    for group in ("family", "link"):
        decode_object(prediction[group], group, f"snapshot.{group}")
    for name, term in prediction["terms"].items():
        kind = term["kind"]
        expected_kind = {
            "Numeric": "numeric",
            "Spline": "spline",
            "Categorical": "categorical",
            "OrderedCategorical": "ordered_categorical",
        }.get(recipe["features"][name]["type"])
        if kind != expected_kind:
            raise MonitoringError(f"snapshot predictor type mismatch for {name!r}")
        if kind == "numeric":
            if set(term) != {"kind", "coefficient"} or not _finite(term["coefficient"]):
                raise MonitoringError("invalid snapshot numeric predictor")
        elif kind == "spline":
            if set(term) != {
                "kind",
                "breaks",
                "coefficients",
                "degree",
                "extrapolation",
                "left_tail",
                "right_tail",
            }:
                raise MonitoringError("invalid snapshot spline fields")
            breaks, coefficients = (
                np.asarray(term["breaks"], dtype=float),
                np.asarray(term["coefficients"], dtype=float),
            )
            if (
                breaks.ndim != 1
                or len(breaks) < 2
                or not np.isfinite(breaks).all()
                or not np.all(np.diff(breaks) > 0)
                or coefficients.shape != (len(breaks) - 1, 4)
                or not np.isfinite(coefficients).all()
                or term["degree"] not in {1, 2, 3}
                or term["extrapolation"] not in {"clip", "error", "extend"}
            ):
                raise MonitoringError("invalid snapshot spline geometry")
            for side in ("left_tail", "right_tail"):
                if term["extrapolation"] == "extend":
                    values = np.asarray(term[side], dtype=float)
                    if values.shape != (4,) or not np.isfinite(values).all():
                        raise MonitoringError("invalid snapshot spline tail")
                elif term[side] is not None:
                    raise MonitoringError("unexpected snapshot spline tail")
        elif kind in {"categorical", "ordered_categorical"}:
            if (
                set(term)
                != {
                    "kind",
                    "string_inputs",
                    "unseen",
                    "canonical_levels",
                    "levels",
                    "report_levels",
                }
                or type(term["string_inputs"]) is not bool
                or term["unseen"] not in {"error", "base"}
            ):
                raise MonitoringError("invalid snapshot categorical predictor")
            for identity in term["canonical_levels"]:
                snapshot_prediction.scalar_value(identity)
            for entries, field in (
                (term["levels"], "log_effect"),
                (term["report_levels"], "log_relativity"),
            ):
                keys = []
                for item in entries:
                    if (
                        set(item) != {"identity", "label", field}
                        or not isinstance(item["label"], str)
                        or not _finite(item[field])
                    ):
                        raise MonitoringError("invalid snapshot categorical effect")
                    snapshot_prediction.scalar_value(item["identity"])
                    keys.append(_canonical_json(item["identity"]))
                if not keys or len(set(keys)) != len(keys):
                    raise MonitoringError("invalid snapshot categorical domain")
        else:
            raise MonitoringError(f"unsupported snapshot predictor kind {kind!r}")
    if type(payload["reference_has_weights"]) is not bool or not isinstance(
        payload["reference_profiles"], dict
    ):
        raise MonitoringError("invalid snapshot reference profiles")
    for profile in payload["reference_profiles"].values():
        for identity, item in profile.items():
            snapshot_prediction.scalar_value(json.loads(identity))
            if (
                set(item) != {"level", "rows", "row_share", "weight", "weight_share"}
                or type(item["rows"]) is not int
                or item["rows"] < 0
                or not _finite(item["row_share"])
                or not 0 <= item["row_share"] <= 1
            ):
                raise MonitoringError("invalid snapshot reference counts")
            for key in ("weight", "weight_share"):
                if payload["reference_has_weights"]:
                    if not _finite(item[key]) or item[key] < 0:
                        raise MonitoringError("invalid snapshot reference weights")
                elif item[key] is not None:
                    raise MonitoringError("unexpected snapshot reference weights")
    structure = payload["fit_contract"]["structure"]
    if _sha256_text(_canonical_json(structure)) != payload["fit_contract"]["structure_sha256"]:
        raise MonitoringError("snapshot fit contract structure digest mismatch")
    _validate_evidence(payload)
    _validate_declared_monitoring_policy(payload)


def _validate_declared_monitoring_policy(payload):
    from pricing_pipeline.modeling.monitoring.snapshot_fitting import (
        SPLINE_CONTROL_FIELDS,
        declared_monitoring_policy,
        monitoring_recipe,
        spline_recipes,
    )

    policy = declared_monitoring_policy(payload)
    if (
        not isinstance(policy, dict)
        or set(policy) != {"schema_version", "splines"}
        or type(policy["schema_version"]) is not int
        or policy["schema_version"] != 1
        or not isinstance(policy["splines"], dict)
        or set(policy["splines"]) != set(spline_recipes(payload["recipe"]))
    ):
        raise MonitoringError("invalid declared monitoring policy fields")
    for controls in policy["splines"].values():
        if not isinstance(controls, dict) or set(controls) != SPLINE_CONTROL_FIELDS:
            raise MonitoringError("invalid declared monitoring spline controls")
    try:
        recipe = monitoring_recipe(payload)
        decode_estimator(
            recipe["estimator"], recipe["features"], recipe["feature_order"], recipe["interactions"]
        )
    except (RecipeError, TypeError, ValueError) as exc:
        raise MonitoringError(f"invalid declared monitoring policy: {exc}") from exc


def _validate_evidence(payload):
    """Cross-check duplicated contract, fitted metadata and aggregate evidence."""
    from pricing_pipeline.modeling.monitoring.contracts import (
        FIT_CONTRACT_SCHEMA,
        FIT_CONTRACT_SCHEMA_VERSION,
        MONITORING_VARIANT_POLICIES,
    )
    from pricing_pipeline.modeling.monitoring.invariants import _normalized_runtime_structure

    recipe, receipt, contract = payload["recipe"], payload["receipt"], payload["fit_contract"]
    order = recipe["feature_order"]
    metadata = {item["source_term_name"]: item for item in receipt["term_metadata"].values()}
    expected_order = order + [
        name for name, item in metadata.items() if item["feature_kind"] == "offset"
    ]
    expected_terms = []
    for number, name in enumerate(expected_order, 1):
        text = _canonical_json(metadata[name])
        expected_terms.append(
            asdict(
                MonitoringTerm(
                    name, metadata[name]["feature_kind"], number, text, _sha256_text(text)
                )
            )
        )
    if payload["terms"] != expected_terms:
        raise MonitoringError("snapshot term evidence does not match its receipt")
    if (
        set(contract)
        != {
            "schema_name",
            "schema_version",
            "superglm_version",
            "structure_sha256",
            "structure",
            "fitted_lambdas",
            "evaluation_grid",
            "variants",
        }
        or contract["schema_name"] != FIT_CONTRACT_SCHEMA
        or contract["schema_version"] != FIT_CONTRACT_SCHEMA_VERSION
        or contract["superglm_version"] != payload["superglm_version"]
        or receipt["superglm_version"] != payload["superglm_version"]
    ):
        raise MonitoringError("invalid snapshot fit contract schema")
    expected_variants = {
        variant.value: asdict(policy) for variant, policy in MONITORING_VARIANT_POLICIES.items()
    }
    if contract["variants"] != expected_variants:
        raise MonitoringError("snapshot monitoring variant policies differ")
    structure = contract["structure"]
    for field, expected in (
        ("model", payload["telemetry"]["model"]),
        ("feature_schema", payload["telemetry"]["features"]),
        ("package_metadata", receipt["package_metadata"]),
        ("term_metadata", receipt["term_metadata"]),
    ):
        if structure[field] != expected:
            raise MonitoringError(f"snapshot contract {field} differs from saved evidence")
    from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline

    text = _canonical_json(payload)
    baseline = SqlBaseline(text, _sha256_text(text))
    if payload["normalized_structure"] != _normalized_runtime_structure(baseline, receipt):
        raise MonitoringError("snapshot normalized structure differs from saved evidence")
    protected = []
    for name, feature in recipe["features"].items():
        spline = feature.get("basis") if feature["type"] == "OrderedCategorical" else feature
        if spline.get("type") == "Spline":
            protected.extend(
                f"{name}.{field}" for field in ("knots", "boundary") if spline[field] is not None
            )
    if payload["protected_geometry_fields"] != sorted(protected):
        raise MonitoringError("snapshot protected geometry differs from constructor settings")
    raw = contract["fitted_lambdas"]
    component_terms = {}
    for component, value in raw.items():
        if not isinstance(component, str) or not _finite(value) or value < 0:
            raise MonitoringError("invalid snapshot fitted lambda")
        candidates = [
            name for name in order if component == name or component.startswith(name + ":")
        ]
        component_terms[component] = max(candidates, key=len) if candidates else None
    expected_lambdas, expected_policies = [], []
    for component, value in sorted(raw.items()):
        name = component_terms[component]
        canonical = (
            name
            if name is not None
            and list(component_terms.values()).count(name) == 1
            and component in {name, name + ":wiggle"}
            else component
        )
        expected_lambdas.append(asdict(MonitoringLambda(name, canonical, float(value), "BASELINE")))
        policy = None
        if name is not None:
            term = metadata[name]
            spline = term.get("spline", term)
            policy = spline["declared"].get("lambda_policy")
            if policy is not None and "mode" not in policy:
                policy = policy.get(component.removeprefix(name + ":"))
        mode = "FIXED" if policy is not None and policy.get("mode") == "fixed" else "ESTIMATED"
        expected_policies.append(asdict(MonitoringLambda(name, canonical, float(value), mode)))
    if (
        payload["lambdas"] != expected_lambdas
        or payload["fitted_lambda_policies"] != expected_policies
    ):
        raise MonitoringError("snapshot lambda rows differ from fitted settings")
    grids = contract["evaluation_grid"]
    if set(grids) != set(order):
        raise MonitoringError("snapshot evaluation grid features differ")
    for name, grid in grids.items():
        if set(grid) != {"kind", "points"}:
            raise MonitoringError("invalid snapshot evaluation grid")
        prediction = payload["prediction"]["terms"][name]
        if prediction["kind"] in {"categorical", "ordered_categorical"}:
            expected = [
                {"identity": row["identity"], "label": row["label"]}
                for row in prediction["report_levels"]
            ]
            if grid["kind"] != "categorical" or grid["points"] != expected:
                raise MonitoringError("snapshot categorical evaluation grid differs")
        elif prediction["kind"] == "numeric":
            if grid != {"kind": "numeric", "points": ["per_unit"]}:
                raise MonitoringError("snapshot numeric evaluation grid differs")
        else:
            points = np.asarray(grid["points"], dtype=float)
            boundary = metadata[name]["fitted"]["boundary"]
            if (
                grid["kind"] != "continuous"
                or points.ndim != 1
                or len(points) < 2
                or not np.isfinite(points).all()
                or not np.array_equal(points, np.linspace(*boundary, len(points)))
            ):
                raise MonitoringError("snapshot continuous evaluation grid differs")
    categorical_names = {
        name
        for name, term in payload["prediction"]["terms"].items()
        if term["kind"] in {"categorical", "ordered_categorical"}
    }
    profiles = payload["reference_profiles"]
    if set(profiles) != categorical_names:
        raise MonitoringError("snapshot reference profile features differ")
    row_totals, weight_totals = [], []
    for profile in profiles.values():
        total = sum(item["rows"] for item in profile.values())
        if total <= 0:
            raise MonitoringError("snapshot reference profile is empty")
        row_totals.append(total)
        mass = (
            sum(item["weight"] for item in profile.values())
            if payload["reference_has_weights"]
            else None
        )
        if mass is not None:
            if mass <= 0:
                raise MonitoringError("snapshot reference profile has no positive weight")
            weight_totals.append(mass)
        for item in profile.values():
            if not math.isclose(
                item["row_share"], item["rows"] / total, rel_tol=1e-12, abs_tol=1e-15
            ) or (
                mass is not None
                and not math.isclose(
                    item["weight_share"], item["weight"] / mass, rel_tol=1e-12, abs_tol=1e-15
                )
            ):
                raise MonitoringError("snapshot reference shares differ from aggregate counts")
    if len(set(row_totals)) > 1 or any(
        not math.isclose(value, weight_totals[0], rel_tol=1e-12) for value in weight_totals
    ):
        raise MonitoringError("snapshot reference profile totals differ")
