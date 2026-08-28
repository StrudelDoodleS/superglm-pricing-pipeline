"""Model-neutral orchestration for aggregate reports from scored predictions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from pricing_pipeline.reporting._underwriter_html import render_underwriter_html
from pricing_pipeline.reporting.diagnostics import _json_safe, _records, calculate_diagnostics
from pricing_pipeline.reporting.evidence import (
    EvidenceRequest,
    ModelEvidence,
    ReportContext,
    collect_model_evidence,
)
from pricing_pipeline.reporting.inputs import (
    ColumnOrValues,
    ComparisonUnit,
    UnderwriterReportError,
    UnderwriterReportOptions,
    UnderwriterReportResult,
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
    resolved_evidence = collect_model_evidence(
        context,
        evidence or {},
        evidence_requests,
    )
    sections = calculate_diagnostics(inputs, resolved_evidence, resolved_options)
    output = Path(output_path).expanduser().resolve()
    if output.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("output_path must end in .html or .htm")

    payload = {
        "metadata": {
            "title": resolved_options.title,
            "problem_type": resolved_options.problem_type.replace("_", " ").title(),
            "tweedie_power": resolved_options.resolved_tweedie_power,
            "rows_used": len(inputs.frame),
            "zero_weight_rows_ignored": inputs.zero_weight_rows_ignored,
            "total_weight": float(inputs.weight.sum()),
            "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "top_k": resolved_options.top_k,
            "minimum_cell_size": resolved_options.minimum_cell_size,
            "semantics": dict(_PROBLEM_SEMANTICS[resolved_options.problem_type]),
        },
        "models": list(inputs.predictions),
        "metrics": _records(sections.metrics),
        "importance": {
            model_name: _records(table.head(resolved_options.top_k))
            for model_name, table in sections.importance.items()
        },
        "relativities": _json_safe(sections.relativities),
        "interactions": _json_safe(sections.interactions),
        "distributions": sections.distributions,
        "movement": sections.movement,
        "curves": sections.curves,
        "double_lift": sections.double_lift,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_underwriter_html(_json_safe(payload)), encoding="utf-8")
    return UnderwriterReportResult(
        output_path=output,
        metrics=sections.metrics,
        importance=sections.importance,
        rows_used=len(inputs.frame),
        zero_weight_rows_ignored=inputs.zero_weight_rows_ignored,
    )


__all__ = [
    "UnderwriterReportError",
    "UnderwriterReportOptions",
    "UnderwriterReportResult",
    "build_scored_model_report",
]
