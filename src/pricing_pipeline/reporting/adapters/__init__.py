"""Translate model-specific artifacts into the reporting evidence types.

``superglm`` reads fitted models; ``rating_workbook`` reads exported workbooks.
The report calculations consume their common ``ModelEvidence`` output.
"""

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
