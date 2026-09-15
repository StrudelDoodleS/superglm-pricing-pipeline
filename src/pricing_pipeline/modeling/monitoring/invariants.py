"""Verify the structural restrictions and canonical evidence of a monitoring fit.

The workflow checks the fitted model; persistence checks the recorded result
before writing its observation."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from typing import Any

from superglm import SuperGLM
from superglm.features.ordered_categorical import OrderedCategorical
from superglm.features.spline import _SplineBase

from pricing_pipeline.modeling.monitoring.contracts import (
    INVARIANT_EVIDENCE_SCHEMA,
    INVARIANT_EVIDENCE_SCHEMA_VERSION,
    MONITORING_VARIANT_POLICIES,
    ModelFitContract,
    MonitoringError,
    MonitoringFitResult,
    MonitoringInvariantEvidence,
    MonitoringLambda,
    MonitoringVariant,
    _canonical_json,
    _required_sha256,
    _sha256_text,
)
from pricing_pipeline.modeling.monitoring.evidence import (
    _canonical_lambda_values,
    _monitoring_result_evidence_sha256,
    _result_lambdas,
)
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
    build_superglm_publication_receipt,
)


def _publication_receipt_payload(
    model: SuperGLM,
    *,
    offset_contract: OffsetExportContract,
    fit_sample_weight_name: str | None,
    export_weight_name: str | None,
    input_transforms: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline

    if isinstance(model, SqlBaseline):
        return model.payload()["receipt"]
    return build_superglm_publication_receipt(
        model,
        offset_contract=offset_contract,
        fit_sample_weight_name=fit_sample_weight_name,
        export_weight_name=export_weight_name,
        input_transforms=input_transforms,
    ).model_dump(mode="json")


def _normalize_spline_structure(metadata: dict[str, Any]) -> None:
    declared = metadata.get("declared", {})
    for field_name in ("boundary", "knots", "lambda_policy"):
        declared.pop(field_name, None)
    metadata.get("effective", {}).pop("knot_strategy_actual", None)
    fitted = metadata.get("fitted", {})
    for field_name in ("boundary", "knots", "lower_bound", "upper_bound"):
        fitted.pop(field_name, None)


def _normalized_runtime_structure(
    model: SuperGLM,
    receipt_payload: Mapping[str, Any],
) -> dict[str, Any]:
    terms = copy.deepcopy(dict(receipt_payload["term_metadata"]))
    for metadata in terms.values():
        kind = str(metadata["feature_kind"])
        if kind == "categorical":
            metadata.get("declared", {}).pop("levels", None)
            effective = metadata.get("effective", {})
            effective.pop("level_source", None)
            effective.pop("pinned_levels", None)
            fitted = metadata.get("fitted", {})
            fitted.pop("non_base_levels", None)
            fitted["levels"] = sorted(fitted["levels"], key=_canonical_json)
        elif kind == "ordered_categorical":
            fitted = metadata.get("fitted", {})
            for field_name in (
                "coefficient_width",
                "non_base_levels",
                "pinned_special_levels",
                "special_coefficient_width",
            ):
                fitted.pop(field_name, None)
            _normalize_spline_structure(metadata["spline"])
        elif kind == "spline":
            _normalize_spline_structure(metadata)
        elif kind == "polynomial":
            fitted = metadata.get("fitted", {})
            fitted.pop("lower_bound", None)
            fitted.pop("upper_bound", None)

    from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline

    telemetry = (
        model.payload()["telemetry"]
        if isinstance(model, SqlBaseline)
        else model.training_telemetry()
    )
    feature_schema = copy.deepcopy(telemetry["features"])
    # Active design-matrix groups may contract when a governed level has no
    # effective rows in a particular snapshot. SuperGLM keeps that level known
    # and pins it to zero/base; the persisted raw term metadata records this.
    # It is observation availability, not a structural contract change.
    feature_schema.pop("groups", None)
    return {
        "model": telemetry["model"],
        "feature_schema": feature_schema,
        "package_metadata": receipt_payload["package_metadata"],
        "term_metadata": terms,
    }


def _geometry_from_receipt(receipt_payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    geometry: dict[str, dict[str, Any]] = {}
    for metadata in receipt_payload["term_metadata"].values():
        term_name = str(metadata["source_term_name"])
        kind = str(metadata["feature_kind"])
        if kind == "ordered_categorical":
            fitted = metadata["spline"]["fitted"]
            geometry[term_name] = {
                "boundary": fitted["boundary"],
                "knots": fitted["knots"],
            }
        elif kind == "spline":
            fitted = metadata["fitted"]
            geometry[term_name] = {
                "boundary": fitted["boundary"],
                "knots": fitted["knots"],
            }
        elif kind == "polynomial":
            fitted = metadata["fitted"]
            geometry[term_name] = {"boundary": [fitted["lower_bound"], fitted["upper_bound"]]}
    return geometry


def _protected_geometry_fields(
    baseline: SuperGLM,
    variant: MonitoringVariant,
    baseline_geometry: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    if variant is not MonitoringVariant.FULL_ADAPTIVE:
        return tuple(
            f"{term_name}.{field_name}"
            for term_name, fields in sorted(baseline_geometry.items())
            for field_name in sorted(fields)
        )

    from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline

    if isinstance(baseline, SqlBaseline):
        return tuple(baseline.payload()["protected_geometry_fields"])

    protected: list[str] = []
    for term_name, configured in baseline._config.feature_templates:
        spline = (
            getattr(configured, "_spline_obj", None)
            if isinstance(configured, OrderedCategorical)
            else configured
        )
        if not isinstance(spline, _SplineBase):
            continue
        if (
            getattr(spline, "_explicit_knots", None) is not None
            or getattr(spline, "_named_knots", None) is not None
        ):
            protected.append(f"{term_name}.knots")
        if getattr(spline, "_explicit_boundary", None) is not None:
            protected.append(f"{term_name}.boundary")
    return tuple(sorted(protected))


def _geometry_value(
    geometry: Mapping[str, Mapping[str, Any]],
    path: str,
) -> Any:
    term_name, field_name = path.rsplit(".", 1)
    if term_name not in geometry or field_name not in geometry[term_name]:
        raise MonitoringError(f"protected spline geometry is missing after refit: {path}")
    return geometry[term_name][field_name]


def _verify_monitoring_invariants(
    baseline: SuperGLM,
    fitted: SuperGLM,
    *,
    variant: MonitoringVariant,
    contract: ModelFitContract,
    offset_contract: OffsetExportContract,
    fit_sample_weight_name: str | None,
    export_weight_name: str | None,
    input_transforms: dict[str, dict[str, Any]] | None = None,
) -> MonitoringInvariantEvidence:
    from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline

    baseline_receipt = _publication_receipt_payload(
        baseline,
        offset_contract=offset_contract,
        fit_sample_weight_name=fit_sample_weight_name,
        export_weight_name=export_weight_name,
        input_transforms=input_transforms,
    )
    fitted_receipt = _publication_receipt_payload(
        fitted,
        offset_contract=offset_contract,
        fit_sample_weight_name=fit_sample_weight_name,
        export_weight_name=export_weight_name,
        input_transforms=input_transforms,
    )

    baseline_structure_json = _canonical_json(
        _normalized_runtime_structure(baseline, baseline_receipt)
    )
    fitted_structure_json = _canonical_json(_normalized_runtime_structure(fitted, fitted_receipt))
    baseline_structure_sha256 = _sha256_text(baseline_structure_json)
    fitted_structure_sha256 = _sha256_text(fitted_structure_json)
    if fitted_structure_sha256 != baseline_structure_sha256:
        raise MonitoringError(
            "post-fit invariant guard rejected a structural change in the model, feature "
            "universe/grouping, basis, or constraint contract"
        )

    baseline_geometry = _geometry_from_receipt(baseline_receipt)
    fitted_geometry = _geometry_from_receipt(fitted_receipt)
    if {term_name: tuple(sorted(fields)) for term_name, fields in baseline_geometry.items()} != {
        term_name: tuple(sorted(fields)) for term_name, fields in fitted_geometry.items()
    }:
        raise MonitoringError("post-fit invariant guard rejected changed geometry components")
    protected_geometry = _protected_geometry_fields(baseline, variant, baseline_geometry)
    changed_geometry = [
        path
        for path in protected_geometry
        if _geometry_value(baseline_geometry, path) != _geometry_value(fitted_geometry, path)
    ]
    if changed_geometry:
        raise MonitoringError(
            "post-fit invariant guard rejected changed protected knot/boundary geometry: "
            + ", ".join(changed_geometry)
        )

    baseline_lambda_rows = (
        tuple(MonitoringLambda(**row) for row in baseline.payload()["fitted_lambda_policies"])
        if isinstance(baseline, SqlBaseline)
        else _result_lambdas(baseline, MonitoringVariant.REESTIMATE_LAMBDA)
    )
    fitted_lambda_rows = (
        fitted.lambdas if isinstance(fitted, SqlBaseline) else _result_lambdas(fitted, variant)
    )
    baseline_lambdas = {row.component_name: row.lambda_value for row in baseline_lambda_rows}
    fitted_lambdas = {row.component_name: row.lambda_value for row in fitted_lambda_rows}
    if set(fitted_lambdas) != set(baseline_lambdas):
        raise MonitoringError("post-fit invariant guard rejected changed lambda components")
    baseline_modes = {row.component_name: row.lambda_mode for row in baseline_lambda_rows}
    fitted_modes = {row.component_name: row.lambda_mode for row in fitted_lambda_rows}
    protected_lambdas = (
        tuple(sorted(baseline_lambdas))
        if variant in {MonitoringVariant.STATIC_SCORE, MonitoringVariant.FROZEN_REFIT}
        else tuple(
            sorted(component for component, mode in baseline_modes.items() if mode == "FIXED")
        )
    )
    changed_lambdas = [
        component
        for component in protected_lambdas
        if fitted_lambdas[component] != baseline_lambdas[component]
    ]
    if changed_lambdas:
        raise MonitoringError(
            "post-fit invariant guard rejected changed fixed lambda values: "
            + ", ".join(changed_lambdas)
        )
    if variant is MonitoringVariant.FROZEN_REFIT and any(
        fitted_modes[component] != "FIXED" for component in fitted_modes
    ):
        raise MonitoringError("post-fit invariant guard found a non-fixed frozen lambda policy")
    if variant is not MonitoringVariant.STATIC_SCORE and any(
        fitted_modes[component] != "FIXED" for component in protected_lambdas
    ):
        raise MonitoringError("post-fit invariant guard found a protected lambda was not fixed")

    diagnostics = (
        {"termination_reason": fitted.payload().get("reml_termination_reason")}
        if isinstance(fitted, SqlBaseline)
        else fitted.reml_diagnostics()
    )
    termination_reason = diagnostics.get("termination_reason")
    if (
        variant is MonitoringVariant.FROZEN_REFIT
        and baseline_lambdas
        and termination_reason != "fixed_lambdas"
    ):
        raise MonitoringError(
            "post-fit invariant guard expected SuperGLM termination_reason='fixed_lambdas'"
        )
    history = (
        []
        if variant is MonitoringVariant.STATIC_SCORE
        else [
            _canonical_lambda_values(fitted, raw_step)
            for raw_step in diagnostics.get("lambda_history", [])
        ]
    )
    if protected_lambdas and variant is not MonitoringVariant.STATIC_SCORE and not history:
        raise MonitoringError("post-fit invariant guard found no fixed-lambda history evidence")
    for step_no, step in enumerate(history):
        changed_at_step = [
            component
            for component in protected_lambdas
            if component not in step or step[component] != baseline_lambdas[component]
        ]
        if changed_at_step:
            raise MonitoringError(
                "post-fit invariant guard rejected a fixed lambda change in REML history "
                f"step {step_no}: " + ", ".join(changed_at_step)
            )

    policy = MONITORING_VARIANT_POLICIES[variant]
    payload = {
        "schema_name": INVARIANT_EVIDENCE_SCHEMA,
        "schema_version": INVARIANT_EVIDENCE_SCHEMA_VERSION,
        "status": "VERIFIED",
        "variant": variant.value,
        "contract_sha256": contract.contract_sha256,
        "contract_structure_sha256": contract.structure_sha256,
        "policy": {
            "refit_coefficients": policy.refit_coefficients,
            "reestimate_lambdas": policy.reestimate_lambdas,
            "reposition_data_driven_knots": policy.reposition_data_driven_knots,
        },
        "structure": {
            "baseline_sha256": baseline_structure_sha256,
            "fitted_sha256": fitted_structure_sha256,
            "exact_match": True,
        },
        "geometry": {
            "baseline": baseline_geometry,
            "fitted": fitted_geometry,
            "protected_fields": list(protected_geometry),
            "protected_exact_match": True,
        },
        "lambdas": {
            "baseline": baseline_lambdas,
            "fitted": fitted_lambdas,
            "baseline_modes": baseline_modes,
            "fitted_modes": fitted_modes,
            "protected_components": list(protected_lambdas),
            "protected_exact_match": True,
            "history": history,
            "history_checked": variant is not MonitoringVariant.STATIC_SCORE,
            "history_exact_for_protected_components": True,
            "termination_reason": termination_reason,
        },
    }
    evidence_json = _canonical_json(payload)
    return MonitoringInvariantEvidence(
        status="VERIFIED",
        evidence_json=evidence_json,
        evidence_sha256=_sha256_text(evidence_json),
    )


def _validate_persistable_invariant_evidence(
    result: MonitoringFitResult,
) -> MonitoringInvariantEvidence:
    evidence = result.invariant_evidence
    if evidence.status != "VERIFIED":
        raise MonitoringError("monitoring persistence requires VERIFIED invariant evidence")
    try:
        payload = evidence.payload()
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MonitoringError("monitoring invariant evidence is not valid JSON") from exc
    if _canonical_json(payload) != evidence.evidence_json:
        raise MonitoringError("monitoring invariant evidence is not canonical JSON")
    if _sha256_text(evidence.evidence_json) != evidence.evidence_sha256:
        raise MonitoringError("monitoring invariant evidence digest does not match its JSON")
    if (
        payload.get("status") != "VERIFIED"
        or payload.get("variant") != result.variant.value
        or payload.get("contract_sha256") != result.contract.contract_sha256
    ):
        raise MonitoringError("monitoring invariant evidence does not identify this fit result")
    return evidence


def _validate_persistable_result_evidence(
    result: MonitoringFitResult,
) -> tuple[str, dict[str, Any]]:
    frame_digest = result.model_frame_sha256
    if (
        not isinstance(frame_digest, str)
        or len(frame_digest) != 64
        or frame_digest != frame_digest.lower()
        or any(character not in "0123456789abcdef" for character in frame_digest)
    ):
        raise MonitoringError(
            "monitoring persistence requires an exact model_frame_sha256 from run_monitoring_fit"
        )
    try:
        fit_configuration = json.loads(result.fit_configuration_json)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MonitoringError("monitoring fit configuration is not valid JSON") from exc
    if _canonical_json(fit_configuration) != result.fit_configuration_json:
        raise MonitoringError("monitoring fit configuration is not canonical JSON")
    baseline = fit_configuration.get("baseline")
    if not isinstance(baseline, dict):
        raise MonitoringError(
            "monitoring persistence requires a verified deployed candidate artifact"
        )
    for field_name in (
        "candidate_artifact_sha256",
        "model_equivalence_sha256",
        "model_frame_sha256",
        "model_source_sha256",
        "package_publication_receipt_sha256",
        "publication_receipt_sha256",
        "row_order_sha256",
    ):
        _required_sha256(baseline.get(field_name), f"baseline {field_name}")
    for field_name in (
        "deployment_id",
        "model_id",
        "model_run_id",
        "rate_package_id",
    ):
        value = baseline.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int | str) or not str(value).strip():
            raise MonitoringError(f"baseline {field_name} is required")
    if not isinstance(baseline.get("manifest_id"), str) or not baseline["manifest_id"].strip():
        raise MonitoringError("baseline manifest_id is required")
    expected = _monitoring_result_evidence_sha256(result)
    if result.result_evidence_sha256 != expected:
        raise MonitoringError("monitoring result evidence digest does not match its details")
    return expected, baseline
