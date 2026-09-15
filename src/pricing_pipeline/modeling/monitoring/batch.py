"""Run all four monitoring variants against one fresh dataset and SQL baseline."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from pricing_pipeline.data.dataset import PricingDataset
from pricing_pipeline.data.manifest import (
    ModelFrameManifestSpec,
    create_model_frame_manifest_with_split,
)
from pricing_pipeline.data.transforms import apply_transforms, transforms_from_metadata
from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.monitoring.baseline import _resolve_monitoring_baseline
from pricing_pipeline.modeling.monitoring.challengers import (
    MonitoringPublicationConfig,
    publish_monitoring_challenger,
)
from pricing_pipeline.modeling.monitoring.contracts import MonitoringError, MonitoringVariant
from pricing_pipeline.modeling.monitoring.data_checks import check_monitoring_data
from pricing_pipeline.modeling.monitoring.persistence import persist_monitoring_fit
from pricing_pipeline.modeling.monitoring.snapshot import SqlBaseline
from pricing_pipeline.modeling.monitoring.workflow import run_monitoring_fit
from pricing_pipeline.models.config import ValidationSplitConfig

logger = logging.getLogger("pricing_pipeline.monitoring")


@dataclass(frozen=True)
class MonitoringReport:
    """Saved observation receipts, metrics and preflight findings for notebook display.

    Each table identifies its monitoring variant. Run rows distinguish champion
    identity from any published challenger package. Fitted models and individual
    source rows are not retained in the report. Evidence-only runs have no
    challenger package IDs, including legacy SQL exposure baselines that cannot
    use automatic challenger publication.
    """

    manifest_id: str
    runs: pd.DataFrame
    metrics: pd.DataFrame
    issues: pd.DataFrame
    drift: pd.DataFrame


def _saved_manifest_roles(engine: Engine, baseline: SqlBaseline, target_column: str):
    """Read the saved offset column without guessing from its display expression."""
    manifest_id = baseline.payload()["bundle_identity"]["manifest_id"]
    if baseline.identity.get("manifest_id") != manifest_id:
        raise MonitoringError("SQL baseline identity does not match its saved manifest")
    schema = schema_names_from_connectable(engine).pricing
    with engine.connect() as connection:
        roles = (
            connection.execute(
                text(f"""SELECT target_column, weight_column, offset_column,
                offset_source_column, offset_label, export_weight_column
                FROM {schema}.DATASET_MANIFEST WHERE manifest_id=:manifest_id"""),
                {"manifest_id": manifest_id},
            )
            .mappings()
            .one_or_none()
        )
    if roles is None:
        raise MonitoringError("SQL baseline dataset manifest is missing")
    offset_contract = baseline.offset_contract
    expected = {
        "target_column": target_column,
        "weight_column": baseline.fit_sample_weight_name,
        "export_weight_column": baseline.export_weight_name,
        "offset_source_column": (
            offset_contract.source_name if offset_contract.handling == "EXPORTED_FACTOR" else None
        ),
        "offset_label": offset_contract.label,
    }
    for name, value in expected.items():
        if roles[name] != value:
            raise MonitoringError(f"{name} does not match the saved SQL baseline manifest")
    if (roles["offset_column"] is None) != (offset_contract.handling == "NONE"):
        raise MonitoringError("offset_column does not match the saved SQL baseline fit contract")
    return roles


def run_monitoring_batch(
    engine: Engine,
    baseline: SqlBaseline,
    dataset: PricingDataset,
    *,
    target_column: str,
    component_role: str = "OTHER",
    created_by: str,
    continuous_points: int = 101,
    max_reml_iter: int = 20,
    reml_tol: float | None = None,
    publication: MonitoringPublicationConfig | None = None,
) -> MonitoringReport:
    """Check, fit and save all four monitoring variants using saved SQL roles.

    Apply the baseline's declared transforms to ``dataset.df``. Check every
    variant before fitting any variant, then finish all fits before writing the
    dated manifest or observations. Each observation has its own transaction;
    a later persistence failure can leave earlier observations saved. Exact
    evidence retries reuse their existing manifest and observation receipts.
    Supplying ``publication`` also exports the three fitted refits as selectable
    challenger packages after saving their observations. It never deploys them.
    Legacy ``ALREADY_APPLIED_SQL_EXPOSURE`` offsets support evidence-only runs;
    automatic challenger publication rejects that contract before any fit.
    """
    if not isinstance(baseline, SqlBaseline):
        raise TypeError("baseline must be a SqlBaseline loaded from SQL")
    if not isinstance(dataset, PricingDataset):
        raise TypeError("dataset must be a PricingDataset with the current as-at column")
    for name, value in (
        ("target_column", target_column),
        ("created_by", created_by),
        ("component_role", component_role),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
    target_column, created_by = target_column.strip(), created_by.strip()
    component_role = component_role.strip().upper()
    if component_role not in {"FREQUENCY", "SEVERITY", "OTHER"}:
        raise ValueError("component_role must be FREQUENCY, SEVERITY, or OTHER")
    baseline, identity, _ = _resolve_monitoring_baseline(baseline)
    model_run_id, deployment_id = baseline.model_run_id, baseline.deployment_id
    if publication is not None:
        if not isinstance(publication, MonitoringPublicationConfig):
            raise TypeError("publication must be a MonitoringPublicationConfig")
        if baseline.offset_contract.handling == "ALREADY_APPLIED_SQL_EXPOSURE":
            raise MonitoringError(
                "offset handling ALREADY_APPLIED_SQL_EXPOSURE does not support automatic "
                "challenger publication. Run run_monitoring_batch without publication "
                "for evidence-only monitoring, or publish a reviewed baseline with "
                "a supported offset export contract."
            )
        for name, actual, expected in (
            ("model_id", publication.model_id, identity["model_id"]),
            ("model_name", publication.model_config.model_name, identity["model_name"]),
            ("target_column", publication.model_config.target_name, target_column),
            (
                "deployment_slot",
                publication.model_config.deployment_slot,
                identity["deployment_slot"],
            ),
        ):
            if actual != expected:
                raise MonitoringError(
                    f"challenger publication {name} does not match the SQL baseline"
                )
    roles = _saved_manifest_roles(engine, baseline, target_column)
    transforms = transforms_from_metadata(baseline.input_transforms)
    df = apply_transforms(dataset.df, transforms)
    features = baseline.feature_names
    required = [*features, target_column]
    required.extend(
        roles[name]
        for name in (
            "weight_column",
            "offset_column",
            "offset_source_column",
            "export_weight_column",
        )
        if roles[name] is not None
    )
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise MonitoringError(
            "monitoring dataset is missing required columns: " + ", ".join(missing)
        )
    manifest_spec = ModelFrameManifestSpec(
        dataset_name=dataset.name,
        source_system=dataset.source,
        data_as_of_date=df[dataset.as_of].iloc[0],
        data_as_of_column=dataset.as_of,
        pk_columns=dataset.key,
        feature_columns=features,
        **roles,
    )
    X = df.loc[:, list(features)]
    y = df[target_column]
    sample_weight = None if roles["weight_column"] is None else df[roles["weight_column"]]
    offset = None if roles["offset_column"] is None else df[roles["offset_column"]]

    checks = {}
    for variant in MonitoringVariant:
        logger.info("Checking %s monitoring inputs", variant.value)
        checks[variant] = check_monitoring_data(
            baseline, X, sample_weight=sample_weight, variant=variant
        )
    for variant, check in checks.items():
        check.raise_for_errors()
        for warning in check.issues.itertuples(index=False):
            logger.warning("%s %s: %s", variant.value, warning.code, warning.message)

    results = []
    for variant in MonitoringVariant:
        logger.info("Running %s", variant.value)
        try:
            result = run_monitoring_fit(
                baseline,
                X,
                y,
                variant=variant,
                sample_weight=sample_weight,
                offset=offset,
                offset_contract=baseline.offset_contract,
                fit_sample_weight_name=baseline.fit_sample_weight_name,
                export_weight_name=baseline.export_weight_name,
                input_transforms=baseline.input_transforms,
                model_frame=df,
                target_column=target_column,
                offset_column=roles["offset_column"],
                continuous_points=continuous_points,
                max_reml_iter=max_reml_iter,
                reml_tol=reml_tol,
            )
        except Exception as exc:
            raise MonitoringError(f"{variant.value} fit failed: {exc}") from exc
        results.append(result)

    manifest = create_model_frame_manifest_with_split(
        engine,
        frame=df,
        spec=manifest_spec,
        validation_split=ValidationSplitConfig(method="none"),
        created_by=created_by,
    )
    runs, metrics = [], []
    for result in results:
        logger.info("Saving %s for manifest %s", result.variant.value, manifest.manifest_id)
        try:
            receipt = persist_monitoring_fit(
                engine,
                result,
                baseline_model_run_id=model_run_id,
                baseline_deployment_id=deployment_id,
                manifest_id=manifest.manifest_id,
                created_by=created_by,
                component_role=component_role,
            )
        except Exception as exc:
            raise MonitoringError(
                f"{result.variant.value} persistence failed after {len(runs)} saved observations: {exc}"
            ) from exc
        published = {}
        if publication is not None and result.variant is not MonitoringVariant.STATIC_SCORE:
            try:
                published = publish_monitoring_challenger(
                    engine,
                    baseline=baseline,
                    result=result,
                    receipt=receipt,
                    df=df,
                    manifest=manifest,
                    manifest_spec=manifest_spec,
                    publication=publication,
                    created_by=created_by,
                )
            except Exception as exc:
                raise MonitoringError(
                    f"{result.variant.value} challenger publication failed: {exc}"
                ) from exc
        runs.append(
            {
                "variant": result.variant.value,
                "role": "CHAMPION"
                if result.variant is MonitoringVariant.STATIC_SCORE
                else "CHALLENGER",
                "model_name": identity["model_name"],
                "definition_revision": identity["recipe_revision"],
                "fit_version": published.get("model_version"),
                "model_id": identity["model_id"],
                "baseline_model_run_id": model_run_id,
                "baseline_deployment_id": deployment_id,
                "baseline_rate_package_id": identity["rate_package_id"],
                "baseline_package_version": identity["package_version"],
                "deployment_slot": identity["deployment_slot"],
                **asdict(receipt),
                **{
                    name: published.get(name)
                    for name in (
                        "model_run_id",
                        "rate_package_id",
                        "package_version",
                        "package_status",
                        "publication_reused",
                    )
                },
            }
        )
        metrics.extend(
            {"variant": result.variant.value, "metric_name": name, "metric_value": value}
            for name, value in result.metrics.items()
        )
        logger.info(
            "%s %s observation %s",
            result.variant.value,
            "reused" if receipt.deduplicated else "saved",
            receipt.monitor_run_id,
        )
    run_df = pd.DataFrame(runs)
    # Preserve integer or string SQL identities when STATIC_SCORE has no package.
    for name in ("model_run_id", "rate_package_id", "package_version"):
        run_df[name] = pd.Series([row[name] for row in runs], dtype=object)
    return MonitoringReport(
        manifest_id=manifest.manifest_id,
        runs=run_df,
        metrics=pd.DataFrame(metrics),
        issues=pd.concat(
            [check.issues.assign(variant=variant.value) for variant, check in checks.items()],
            ignore_index=True,
        ),
        drift=pd.concat(
            [check.drift.assign(variant=variant.value) for variant, check in checks.items()],
            ignore_index=True,
        ),
    )


__all__ = ["MonitoringReport", "run_monitoring_batch"]
