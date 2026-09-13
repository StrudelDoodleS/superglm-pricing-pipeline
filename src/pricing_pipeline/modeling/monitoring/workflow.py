"""Run one monitoring comparison through its explicit verification and fitting steps.

Resolve the baseline, bind data, reconstruct and fit the selected variant,
check invariants, then return MonitoringFitResult. Persistence is a separate call."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd
from superglm import SuperGLM

from pricing_pipeline.data.transforms import transforms_from_metadata, transforms_metadata
from pricing_pipeline.modeling.monitoring.baseline import (
    _bind_monitoring_model_frame,
    _resolve_monitoring_baseline,
)
from pricing_pipeline.modeling.monitoring.contracts import (
    MonitoringError,
    MonitoringFitResult,
    MonitoringVariant,
)
from pricing_pipeline.modeling.monitoring.data_checks import _require_compatible_monitoring_data
from pricing_pipeline.modeling.monitoring.evidence import (
    _monitoring_fit_configuration_json,
    _monitoring_result_evidence_sha256,
    _result_lambdas,
    _result_metrics,
    _result_relativities,
    _result_terms,
)
from pricing_pipeline.modeling.monitoring.fitting import (
    build_model_fit_contract,
    materialize_monitoring_model,
)
from pricing_pipeline.modeling.monitoring.invariants import _verify_monitoring_invariants
from pricing_pipeline.publishing.metadata import (
    OffsetExportContract,
)
from pricing_pipeline.workbench.core import Candidate


def run_monitoring_fit(
    baseline_model: SuperGLM | Candidate,
    X: pd.DataFrame,
    y: Any,
    *,
    variant: MonitoringVariant | str,
    sample_weight: Any = None,
    offset: Any = None,
    offset_contract: OffsetExportContract | None = None,
    fit_sample_weight_name: str | None = None,
    export_weight_name: str | None = None,
    input_transforms: dict[str, dict[str, Any]] | None = None,
    continuous_points: int = 101,
    max_reml_iter: int = 20,
    reml_tol: float | None = None,
    runtime_validation: str | bool = "auto",
    model_frame: pd.DataFrame | None = None,
    target_column: str | None = None,
    offset_column: str | None = None,
) -> MonitoringFitResult:
    """Score or refit a baseline under the selected monitoring variant.

    Verify the baseline and supplied data, materialize the permitted model,
    then extract metrics and relativities and check its frozen structure.
    Return ``MonitoringFitResult`` for ``persist_monitoring_fit``.
    """
    baseline, baseline_identity, baseline_bundle = _resolve_monitoring_baseline(baseline_model)
    preparation = (
        transforms_metadata(
            transforms_from_metadata({} if input_transforms is None else input_transforms)
        )
        or None
    )
    resolved_variant = MonitoringVariant(variant)
    if not isinstance(X, pd.DataFrame) or X.empty:
        raise ValueError("X must be a non-empty pandas DataFrame")
    if len(X) != len(y):
        raise ValueError("X and y must have the same row count")
    if baseline_bundle is None:
        resolved_offset = offset_contract or OffsetExportContract(handling="NONE")
    else:
        resolved_offset = baseline_bundle.offset_contract
        baseline_preparation = getattr(baseline_bundle, "input_transforms", None)
        if input_transforms is not None and preparation != baseline_preparation:
            raise MonitoringError(
                "input_transforms does not match the verified baseline candidate artifact"
            )
        preparation = baseline_preparation
        if offset_contract is not None and offset_contract != resolved_offset:
            raise MonitoringError(
                "offset_contract does not match the verified baseline candidate artifact"
            )
        for supplied, expected, field_name in (
            (
                fit_sample_weight_name,
                baseline_bundle.fit_sample_weight_name,
                "fit_sample_weight_name",
            ),
            (
                export_weight_name,
                baseline_bundle.export_weight_name,
                "export_weight_name",
            ),
        ):
            if supplied is not None and supplied != expected:
                raise MonitoringError(
                    f"{field_name} does not match the verified baseline candidate artifact"
                )
        fit_sample_weight_name = baseline_bundle.fit_sample_weight_name
        export_weight_name = baseline_bundle.export_weight_name
        if fit_sample_weight_name is not None and sample_weight is None:
            raise MonitoringError(
                "sample_weight is required by the verified baseline candidate fit contract"
            )
        if resolved_offset.handling != "NONE" and offset is None:
            raise MonitoringError(
                "offset is required by the verified baseline candidate fit contract"
            )
        if resolved_offset.handling == "NONE" and offset is not None:
            raise MonitoringError(
                "offset was not used by the verified baseline candidate fit contract"
            )
    model_frame_sha256 = _bind_monitoring_model_frame(
        X,
        y,
        model_frame=model_frame,
        target_column=target_column,
        sample_weight=sample_weight,
        fit_sample_weight_name=fit_sample_weight_name,
        offset=offset,
        offset_column=offset_column,
    )
    fit_configuration_json = _monitoring_fit_configuration_json(
        variant=resolved_variant,
        baseline_identity=baseline_identity,
        model_frame_sha256=model_frame_sha256,
        target_column=(None if target_column is None else target_column.strip()),
        fit_sample_weight_name=fit_sample_weight_name,
        offset_column=None if offset_column is None else offset_column.strip(),
        offset_contract=resolved_offset,
        continuous_points=continuous_points,
        max_reml_iter=max_reml_iter,
        reml_tol=reml_tol,
        runtime_validation=runtime_validation,
    )
    _require_compatible_monitoring_data(
        baseline,
        X,
        sample_weight,
        static_score=resolved_variant is MonitoringVariant.STATIC_SCORE,
    )
    contract = build_model_fit_contract(
        baseline,
        offset_contract=resolved_offset,
        fit_sample_weight_name=fit_sample_weight_name,
        export_weight_name=export_weight_name,
        input_transforms=preparation,
        continuous_points=continuous_points,
    )
    if resolved_variant is MonitoringVariant.STATIC_SCORE:
        fitted = baseline
    else:
        fitted = materialize_monitoring_model(baseline, resolved_variant)
        fitted.fit_reml(
            X,
            np.asarray(y),
            sample_weight=sample_weight,
            offset=offset,
            max_reml_iter=max_reml_iter,
            reml_tol=reml_tol,
            runtime_validation=runtime_validation,
        )
    invariant_evidence = _verify_monitoring_invariants(
        baseline,
        fitted,
        variant=resolved_variant,
        contract=contract,
        offset_contract=resolved_offset,
        fit_sample_weight_name=fit_sample_weight_name,
        export_weight_name=export_weight_name,
        input_transforms=preparation,
    )
    payload = contract.payload()
    result = MonitoringFitResult(
        variant=resolved_variant,
        contract=contract,
        fitted_model=fitted,
        terms=_result_terms(
            fitted,
            offset_contract=resolved_offset,
            fit_sample_weight_name=fit_sample_weight_name,
            export_weight_name=export_weight_name,
        ),
        lambdas=_result_lambdas(fitted, resolved_variant),
        relativities=_result_relativities(fitted, payload["evaluation_grid"]),
        metrics=_result_metrics(fitted, X, y, sample_weight, offset),
        invariant_evidence=invariant_evidence,
        model_frame_sha256=model_frame_sha256,
        fit_configuration_json=fit_configuration_json,
        result_evidence_sha256="",
    )
    return replace(
        result,
        result_evidence_sha256=_monitoring_result_evidence_sha256(result),
    )
