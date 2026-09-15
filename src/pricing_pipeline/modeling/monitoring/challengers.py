"""Publish the exact fitted monitoring refit and discard its temporary model files.

The saved package and SQL snapshot support review, scoring and promotion. This
path does not retain a local candidate bundle for the file-based model editor.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd
from sqlalchemy.engine import Engine

from pricing_pipeline.data.manifest import (
    DatasetManifestResult,
    ModelFrameManifestSpec,
    model_frame_evidence,
)
from pricing_pipeline.infra.config import Settings
from pricing_pipeline.modeling.monitoring.contracts import (
    MonitoringError,
    MonitoringFitResult,
    MonitoringVariant,
    PersistedMonitoringRun,
)
from pricing_pipeline.modeling.monitoring.evidence import (
    _monitoring_result_evidence_sha256,
    _result_lambdas,
    _result_metrics,
    _result_relativities,
    _result_terms,
)
from pricing_pipeline.modeling.monitoring.invariants import (
    _validate_persistable_result_evidence,
    _verify_monitoring_invariants,
)
from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline
from pricing_pipeline.modeling.standard_superglm import (
    ModelInputs,
    canonical_row_identity_index,
    export_fitted_superglm_build,
)
from pricing_pipeline.models.config import ModelBuildConfig, ValidationSplitConfig
from pricing_pipeline.publishing.monitoring import find_monitoring_publication
from pricing_pipeline.publishing.publish import PublicationRequest, publish_candidate
from pricing_pipeline.publishing.recipes import inherit_run_recipe
from pricing_pipeline.publishing.sqlite import resolve_sqlite_model_version
from pricing_pipeline.publishing.sqlserver import resolve_model_version_for_export

logger = logging.getLogger("pricing_pipeline.monitoring")


@dataclass(frozen=True)
class MonitoringPublicationConfig:
    """Publication destination and the registered model receiving the challengers."""

    settings: Settings
    model_config: ModelBuildConfig
    model_id: int


def _verify_fitted_result(baseline, result, df, manifest_spec):
    """Re-extract evidence from the live estimator before exporting its coefficients."""
    _validate_persistable_result_evidence(result)
    X = df.loc[:, list(baseline.feature_names)]
    y = df[manifest_spec.target_column]
    sample_weight = None if manifest_spec.weight_column is None else df[manifest_spec.weight_column]
    offset = None if manifest_spec.offset_column is None else df[manifest_spec.offset_column]
    roles = {
        "offset_contract": baseline.offset_contract,
        "fit_sample_weight_name": baseline.fit_sample_weight_name,
        "export_weight_name": baseline.export_weight_name,
    }
    fitted = result.fitted_model
    current = replace(
        result,
        terms=_result_terms(fitted, **roles),
        lambdas=_result_lambdas(fitted, result.variant),
        relativities=_result_relativities(fitted, result.contract.payload()["evaluation_grid"]),
        metrics=_result_metrics(fitted, X, y, sample_weight, offset),
        model_frame_sha256=model_frame_evidence(df)[0],
        invariant_evidence=_verify_monitoring_invariants(
            baseline,
            fitted,
            variant=result.variant,
            contract=result.contract,
            input_transforms=baseline.input_transforms,
            **roles,
        ),
    )
    if _monitoring_result_evidence_sha256(current) != result.result_evidence_sha256:
        raise MonitoringError(
            "the fitted estimator no longer matches the recorded monitoring evidence"
        )


def publish_monitoring_challenger(
    engine: Engine,
    *,
    baseline: SqlBaseline,
    result: MonitoringFitResult,
    receipt: PersistedMonitoringRun,
    df: pd.DataFrame,
    manifest: DatasetManifestResult,
    manifest_spec: ModelFrameManifestSpec,
    publication: MonitoringPublicationConfig,
    created_by: str,
) -> dict[str, Any]:
    """Publish or reuse the package linked to one sealed, exact refit observation.

    Export the supplied estimator without cloning, cross-validation or another
    fit. The temporary workbook, receipt and training bundle exist only while
    the publisher validates and captures their SQL state.
    """
    if result.variant is MonitoringVariant.STATIC_SCORE:
        raise MonitoringError("STATIC_SCORE is the champion observation and has no challenger")
    existing = find_monitoring_publication(engine, receipt.monitor_run_id)
    if existing is not None:
        logger.info(
            "%s reuses challenger package %s", result.variant.value, existing["package_version"]
        )
        return {**existing, "publication_reused": True}
    _verify_fitted_result(baseline, result, df, manifest_spec)
    if manifest.model_frame_sha256 != result.model_frame_sha256:
        raise MonitoringError("challenger manifest does not match the fitted monitoring evidence")
    config = publication.model_config
    no_validation = ValidationSplitConfig(
        method="none", n_splits=None, random_state=None, shuffle=False
    )
    with engine.connect() as connection:
        recipe_capture = inherit_run_recipe(
            connection, model_run_id=baseline.model_run_id, model_config=config
        )
    row_ids = df.loc[:, list(manifest_spec.pk_columns)].copy()
    aligned = df.copy()
    aligned.index = canonical_row_identity_index(row_ids)
    inputs = ModelInputs(
        X=aligned.loc[:, list(baseline.feature_names)],
        y=aligned[manifest_spec.target_column],
        row_ids=row_ids,
        sample_weight=None
        if manifest_spec.weight_column is None
        else aligned[manifest_spec.weight_column],
        sample_weight_name=manifest_spec.weight_column,
        offset=None
        if manifest_spec.offset_column is None
        else aligned[manifest_spec.offset_column],
        offset_source=None
        if manifest_spec.offset_source_column is None
        else aligned[manifest_spec.offset_source_column],
        offset_source_name=manifest_spec.offset_source_column,
        export_weight=None
        if manifest_spec.export_weight_column is None
        else aligned[manifest_spec.export_weight_column],
        export_weight_name=manifest_spec.export_weight_column,
    )
    export_id = f"monitoring_{receipt.monitor_run_id}"
    reserve = (
        resolve_sqlite_model_version
        if engine.dialect.name == "sqlite"
        else resolve_model_version_for_export
    )
    model_version = reserve(engine, model_name=config.model_name, export_id=export_id)
    root = Path(publication.settings.workbench_artifact_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="monitoring-", dir=root) as directory:
        build = export_fitted_superglm_build(
            frame=df,
            inputs=inputs,
            fitted_model=result.fitted_model,
            telemetry=result.fitted_model.training_telemetry(),
            manifest=manifest,
            manifest_spec=manifest_spec,
            output_dir=Path(directory) / "candidate",
            model_id=publication.model_id,
            model_config=replace(config, validation_split=no_validation),
            model_kind="RAW",
            model_version=model_version,
            export_id=export_id,
            effective_from=None,
            model_source_sha256=baseline.identity["model_source_sha256"],
            created_by=created_by,
            offset_contract=baseline.offset_contract,
            input_transforms=baseline.input_transforms,
            recipe_capture=recipe_capture,
            monitor_run_id=receipt.monitor_run_id,
        )
        published = publish_candidate(
            engine,
            PublicationRequest(
                build=build,
                model_config=config,
                execution_name="monitoring",
                execution_id=receipt.monitor_run_id,
                allowed_artifact_root=root,
            ),
        )
    logger.info("%s saved challenger package %s", result.variant.value, published.package_version)
    return {**asdict(published), "publication_reused": published.was_existing}


__all__ = ["MonitoringPublicationConfig"]
