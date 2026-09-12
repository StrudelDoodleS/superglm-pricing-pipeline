"""Modeling exports, loaded on demand to keep build-evidence imports acyclic."""

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
