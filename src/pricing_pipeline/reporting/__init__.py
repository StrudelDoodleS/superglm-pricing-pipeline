"""Create offline model-comparison reports from existing predictions.

Use ``build_scored_model_report`` for scored data or
``build_underwriter_report`` to include optional model evidence. These reports
contain aggregate diagnostics and do not publish or deploy models.
"""

from pricing_pipeline.reporting.inputs import (
    UnderwriterReportError,
    UnderwriterReportOptions,
    UnderwriterReportResult,
)
from pricing_pipeline.reporting.report import (
    ModelLikelihoodSpec,
    build_scored_model_report,
    build_underwriter_report,
)

__all__ = [
    "ModelLikelihoodSpec",
    "UnderwriterReportError",
    "UnderwriterReportOptions",
    "UnderwriterReportResult",
    "build_scored_model_report",
    "build_underwriter_report",
]
