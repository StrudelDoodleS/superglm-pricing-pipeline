"""Linear workflow for aggregate model-review reports."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from pricing_pipeline.reporting._underwriter_html import render_underwriter_html
from pricing_pipeline.reporting.diagnostics import (
    DiagnosticSections,
    _json_safe,
    _records,
    calculate_diagnostics,
)
from pricing_pipeline.reporting.evidence import (
    EvidenceRequest,
    ModelEvidence,
    ReportContext,
    collect_model_evidence,
)
from pricing_pipeline.reporting.inputs import (
    ColumnOrValues,
    ComparisonUnit,
    ProblemType,
    UnderwriterReportOptions,
    UnderwriterReportResult,
    ValidatedReportInputs,
    normalize_report_inputs,
)

_PROBLEM_SEMANTICS: Mapping[str, Mapping[str, str]] = {
    "frequency": {
        "response": "Claim frequency",
        "prediction": "Predicted claim frequency",
        "volume": "Exposure",
        "curve_x": "Cumulative exposure share",
        "curve_y": "Cumulative claim-count share",
    },
    "severity": {
        "response": "Claim severity",
        "prediction": "Predicted claim severity",
        "volume": "Claim count",
        "curve_x": "Cumulative claim-count share",
        "curve_y": "Cumulative claim-cost share",
    },
    "burn_cost": {
        "response": "Burn cost",
        "prediction": "Predicted burn cost",
        "volume": "Exposure",
        "curve_x": "Cumulative exposure share",
        "curve_y": "Cumulative claim-cost share",
    },
}


@dataclass(frozen=True)
class ModelLikelihoodSpec:
    """Training-fitted distribution metadata for exact holdout scoring."""

    tweedie_power: float
    dispersion: float

    def __post_init__(self) -> None:
        if isinstance(self.tweedie_power, bool):
            raise TypeError("tweedie_power must be numeric, not boolean")
        if isinstance(self.dispersion, bool):
            raise TypeError("dispersion must be numeric, not boolean")
        power = float(self.tweedie_power)
        dispersion = float(self.dispersion)
        if not math.isfinite(power) or not 1.0 <= power <= 2.0:
            raise ValueError("tweedie_power must be finite and between 1 and 2")
        if not math.isfinite(dispersion) or dispersion <= 0.0:
            raise ValueError("dispersion must be finite and strictly positive")
        if power == 1.0 and dispersion != 1.0:
            raise ValueError("Poisson likelihood uses fixed dispersion=1")
        object.__setattr__(self, "tweedie_power", power)
        object.__setattr__(self, "dispersion", dispersion)


def _coerce_model_likelihoods(
    values: Mapping[str, ModelLikelihoodSpec | Mapping[str, Any]],
    *,
    prediction_names: Sequence[str],
    problem_type: ProblemType,
) -> dict[str, ModelLikelihoodSpec]:
    normalized_values = [(str(raw_name).strip(), raw_spec) for raw_name, raw_spec in values.items()]
    unknown = {name for name, _ in normalized_values} - set(prediction_names)
    if unknown:
        raise ValueError(
            "model_likelihoods contains models without predictions: " + ", ".join(sorted(unknown))
        )
    expected_power = {"frequency": 1.0, "severity": 2.0}.get(problem_type)
    resolved: dict[str, ModelLikelihoodSpec] = {}
    for name, raw_spec in normalized_values:
        if isinstance(raw_spec, ModelLikelihoodSpec):
            spec = raw_spec
        elif isinstance(raw_spec, Mapping):
            unknown_fields = set(raw_spec) - {"tweedie_power", "dispersion"}
            missing_fields = {"tweedie_power", "dispersion"} - set(raw_spec)
            if unknown_fields:
                raise ValueError(
                    f"model_likelihoods[{name!r}] has unknown fields: "
                    + ", ".join(sorted(unknown_fields))
                )
            if missing_fields:
                raise ValueError(
                    f"model_likelihoods[{name!r}] is missing fields: "
                    + ", ".join(sorted(missing_fields))
                )
            spec = ModelLikelihoodSpec(
                tweedie_power=raw_spec["tweedie_power"],
                dispersion=raw_spec["dispersion"],
            )
        else:
            raise TypeError(f"model_likelihoods[{name!r}] must be a ModelLikelihoodSpec or mapping")
        if expected_power is not None and spec.tweedie_power != expected_power:
            raise ValueError(f"model_likelihoods[{name!r}] power does not match {problem_type}")
        if problem_type == "burn_cost" and not 1.0 < spec.tweedie_power < 2.0:
            raise ValueError(
                f"model_likelihoods[{name!r}] burn-cost power must be strictly between 1 and 2"
            )
        resolved[name] = spec
    return resolved


def _validate_normalized_model_names(values: Mapping[str, object], label: str) -> None:
    seen: set[str] = set()
    for raw_name in values:
        name = str(raw_name).strip()
        if name in seen:
            raise ValueError(f"{label} contains duplicate normalized model name: {name!r}")
        seen.add(name)


def validate_report_output_path(output_path: str | Path) -> Path:
    """Resolve and validate the requested HTML report path."""
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("output_path must end in .html or .htm")
    return output


def assemble_report_payload(
    inputs: ValidatedReportInputs,
    model_evidence: Mapping[str, ModelEvidence],
    diagnostics: DiagnosticSections,
    options: UnderwriterReportOptions,
) -> dict[str, Any]:
    """Assemble the aggregate-only payload consumed by the HTML renderer."""
    return {
        "metadata": {
            "title": options.title,
            "problem_type": options.problem_type.replace("_", " ").title(),
            "tweedie_power": options.resolved_tweedie_power,
            "rows_used": len(inputs.frame),
            "zero_weight_rows_ignored": inputs.zero_weight_rows_ignored,
            "total_weight": float(inputs.weight.sum()),
            "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "top_k": options.top_k,
            "minimum_cell_size": options.minimum_cell_size,
            "semantics": dict(_PROBLEM_SEMANTICS[options.problem_type]),
        },
        "models": list(inputs.predictions),
        "metrics": _records(diagnostics.metrics),
        "importance": {
            model_name: _records(table.head(options.top_k))
            for model_name, table in diagnostics.importance.items()
        },
        "relativities": _json_safe(diagnostics.relativities),
        "interactions": _json_safe(diagnostics.interactions),
        "distributions": diagnostics.distributions,
        "movement": diagnostics.movement,
        "curves": diagnostics.curves,
        "double_lift": diagnostics.double_lift,
    }


def write_report_html(output: Path, payload: Mapping[str, Any]) -> None:
    """Render and write one self-contained report document."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_underwriter_html(_json_safe(payload)), encoding="utf-8")


def build_scored_model_report(
    frame: pd.DataFrame,
    *,
    actual: ColumnOrValues,
    predictions: Mapping[str, ColumnOrValues],
    sample_weight: ColumnOrValues,
    features: Sequence[str],
    output_path: str | Path,
    evidence: Mapping[str, ModelEvidence] | None = None,
    evidence_requests: Sequence[EvidenceRequest] = (),
    offset: ColumnOrValues | None = None,
    comparison_unit: ComparisonUnit | None = None,
    options: UnderwriterReportOptions | None = None,
) -> UnderwriterReportResult:
    """Write a self-contained aggregate report from scored model outputs."""
    resolved_options = options or UnderwriterReportOptions()
    inputs = normalize_report_inputs(
        frame,
        actual=actual,
        predictions=predictions,
        sample_weight=sample_weight,
        features=features,
        offset=offset,
        comparison_unit=comparison_unit,
        options=resolved_options,
    )
    context = ReportContext(
        frame=inputs.frame,
        actual=inputs.actual,
        predictions=inputs.predictions,
        weight=inputs.weight,
        features=inputs.features,
        comparison_unit_codes=inputs.comparison_unit_codes,
        comparison_units=inputs.comparison_units,
        minimum_cell_size=resolved_options.minimum_cell_size,
        problem_type=resolved_options.problem_type,
        deviance_power=resolved_options.resolved_tweedie_power,
        offset=inputs.offset,
    )
    model_evidence = collect_model_evidence(context, evidence or {}, evidence_requests)
    diagnostics = calculate_diagnostics(inputs, model_evidence, resolved_options)
    output = validate_report_output_path(output_path)
    payload = assemble_report_payload(inputs, model_evidence, diagnostics, resolved_options)
    write_report_html(output, payload)
    return UnderwriterReportResult(
        output_path=output,
        metrics=diagnostics.metrics,
        importance=diagnostics.importance,
        rows_used=len(inputs.frame),
        zero_weight_rows_ignored=inputs.zero_weight_rows_ignored,
    )


def build_underwriter_report(
    frame: pd.DataFrame,
    *,
    actual: ColumnOrValues,
    predictions: Mapping[str, ColumnOrValues],
    sample_weight: ColumnOrValues,
    features: Sequence[str],
    output_path: str | Path,
    superglm_models: Mapping[str, Any] | None = None,
    rating_workbooks: Mapping[str, str | Path] | None = None,
    model_likelihoods: Mapping[
        str,
        ModelLikelihoodSpec | Mapping[str, Any],
    ]
    | None = None,
    offset: ColumnOrValues | None = None,
    comparison_unit: ComparisonUnit | None = None,
    options: UnderwriterReportOptions | None = None,
) -> UnderwriterReportResult:
    """Build the canonical report with optional legacy SuperGLM evidence.

    Supplied likelihood values are training metadata. For a fitted object they
    validate its fitted likelihood and never replace it. When the same model
    also has a rating workbook, the richer fitted-object evidence takes
    precedence, matching the historical facade behavior.
    """
    resolved_options = options or UnderwriterReportOptions()
    _validate_normalized_model_names(predictions, "predictions")
    _validate_normalized_model_names(superglm_models or {}, "superglm_models")
    _validate_normalized_model_names(rating_workbooks or {}, "rating_workbooks")
    _validate_normalized_model_names(model_likelihoods or {}, "model_likelihoods")
    resolved_likelihoods = _coerce_model_likelihoods(
        model_likelihoods or {},
        prediction_names=tuple(str(name).strip() for name in predictions),
        problem_type=resolved_options.problem_type,
    )
    requests: list[EvidenceRequest] = []
    fitted_models = {
        str(raw_name).strip(): model for raw_name, model in (superglm_models or {}).items()
    }

    if fitted_models:
        from pricing_pipeline.reporting.adapters.superglm import SuperGLMReportAdapter

        for model_name, model in fitted_models.items():
            spec = resolved_likelihoods.get(model_name)
            requests.append(
                EvidenceRequest(
                    model_name,
                    SuperGLMReportAdapter(
                        tweedie_power=None if spec is None else spec.tweedie_power,
                        dispersion=None if spec is None else spec.dispersion,
                        n_points=resolved_options.relativity_points,
                        interaction_points=resolved_options.interaction_points,
                    ),
                    model,
                )
            )

    workbook_sources = {
        str(raw_name).strip(): source
        for raw_name, source in (rating_workbooks or {}).items()
        if str(raw_name).strip() not in fitted_models
    }
    if workbook_sources:
        from pricing_pipeline.reporting.adapters.rating_workbook import RatingWorkbookAdapter

        requests.extend(
            EvidenceRequest(model_name, RatingWorkbookAdapter(), source)
            for model_name, source in workbook_sources.items()
        )

    supplied_only = {
        model_name: spec
        for model_name, spec in resolved_likelihoods.items()
        if model_name not in fitted_models
    }
    if supplied_only:
        from pricing_pipeline.reporting.adapters.superglm import SuppliedTweedieLikelihoodAdapter

        requests.extend(
            EvidenceRequest(
                model_name,
                SuppliedTweedieLikelihoodAdapter(
                    tweedie_power=spec.tweedie_power,
                    dispersion=spec.dispersion,
                ),
                None,
            )
            for model_name, spec in supplied_only.items()
        )

    return build_scored_model_report(
        frame,
        actual=actual,
        predictions=predictions,
        sample_weight=sample_weight,
        features=features,
        output_path=output_path,
        evidence_requests=tuple(requests),
        offset=offset,
        comparison_unit=comparison_unit,
        options=resolved_options,
    )


__all__ = [
    "ModelLikelihoodSpec",
    "build_scored_model_report",
    "build_underwriter_report",
]
