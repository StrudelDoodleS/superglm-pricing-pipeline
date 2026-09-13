"""Fit models, preserve reusable configuration and run monitoring refits.

``standard_superglm`` builds training evidence; ``recipes`` saves declared
configuration; ``monitoring`` compares controlled refits with a baseline.
Exports load on first access to avoid circular build-evidence imports.
Notebook callers use ``pricing_pipeline.notebook``.
"""

from importlib import import_module

__all__ = [
    "CVEvidence",
    "FoldMetric",
    "ModelInputs",
    "PrecomputedSplitter",
    "StandardSuperGLMError",
    "cv_result_to_records",
    "run_cross_validation",
    "run_standard_superglm_build",
]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(name)
    value = getattr(import_module("pricing_pipeline.modeling.standard_superglm"), name)
    globals()[name] = value
    return value
