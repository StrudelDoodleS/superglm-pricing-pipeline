"""Fit pricing models, save their evidence and rating tables, and deploy to SQL.

Start with ``pricing_pipeline.notebook`` for model workflows or
``pricing_pipeline.reporting`` for reports from existing predictions.
The package root exposes the installed version.
"""

from importlib.metadata import version

__version__ = version("superglm-pricing-pipeline")
