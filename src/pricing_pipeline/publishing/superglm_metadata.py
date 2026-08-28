"""Compatibility imports for the canonical publication metadata module."""

from pricing_pipeline.publishing import metadata as _metadata

EXTRACTOR_VERSION = _metadata.EXTRACTOR_VERSION
_grouping_metadata = _metadata._grouping_metadata
_json_value = _metadata._json_value
_spline_kind = _metadata._spline_kind
build_superglm_publication_receipt = _metadata.build_superglm_publication_receipt

__all__ = ["EXTRACTOR_VERSION", "build_superglm_publication_receipt"]
