"""Identify datasets and preserve the rows used for fitting and validation.

``dataset`` owns analyst snapshots; ``transforms`` prepares model columns;
``manifest`` records SQL provenance and split evidence. Notebook callers
import the supported helpers from ``pricing_pipeline.notebook``.
"""
