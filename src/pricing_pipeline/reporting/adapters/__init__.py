"""Model-specific evidence adapters for aggregate reporting."""

from pricing_pipeline.reporting.adapters.rating_workbook import RatingWorkbookAdapter
from pricing_pipeline.reporting.adapters.superglm import (
    SuperGLMReportAdapter,
    SuppliedTweedieLikelihoodAdapter,
)

__all__ = [
    "RatingWorkbookAdapter",
    "SuperGLMReportAdapter",
    "SuppliedTweedieLikelihoodAdapter",
]
