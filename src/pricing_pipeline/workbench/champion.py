"""Review published SQL versions and promote the exact reviewed selection.

Review reads package, dataset, monitoring, and metric rows without loading model
files. Promotion remains an explicit call and retains the champion identity
observed during review, even when that champion changes before deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.models.config import ModelBuildConfig
from pricing_pipeline.publishing.deployment import (
    DeploymentError,
    DeploymentResult,
    deploy_rate_package,
)


class ModelVersionReviewError(DeploymentError):
    """The selected version has no unambiguous published SQL identity."""


_METRIC_COLUMNS = (
    "role",
    "model_run_id",
    "monitor_run_id",
    "manifest_id",
    "data_as_of_date",
    "metric_name",
    "metric_value",
    "metric_scope",
)


@dataclass(frozen=True)
class ReviewedModelVersion:
    """A selected SQL version and the champion visible when it was reviewed.

    Display tables are new copies. Changing them cannot change the package or
    expected deployment IDs passed to promotion.
    """

    engine: Any = field(repr=False, compare=False)
    model_config: ModelBuildConfig
    model_id: int
    model_name: str
    package_version: int
    rate_package_id: int
    model_run_id: int | str
    model_version: str
    definition_revision: int | None
    role: str
    refit_type: str
    published_at: Any
    manifest_id: str
    data_as_of_date: Any
    model_kind: str
    monitoring_variant: str | None
    monitor_run_id: str | None
    baseline_data_as_of_date: Any
    current_rate_package_id: int | None
    current_deployment_id: int | None
    current_package_version: int | None
    current_model_run_id: int | str | None
    current_manifest_id: str | None
    current_data_as_of_date: Any
    _metric_rows: tuple[tuple[Any, ...], ...] = field(repr=False)

    @property
    def deployment_slot(self) -> str:
        return self.model_config.deployment_slot.strip().upper()

    @property
    def fit_version(self) -> str:
        """Legacy fit identifier; definition_revision identifies the model recipe."""
        return self.model_version

    @property
    def summary(self) -> pd.DataFrame:
        """Show the selected version and its reviewed champion, with dataset dates."""
        return pd.DataFrame(
            [
                {
                    "model_name": self.model_name,
                    "role": self.role,
                    "definition_revision": self.definition_revision,
                    "refit_type": self.refit_type,
                    "data_as_of_date": self.data_as_of_date,
                    "published_at": self.published_at,
                    "deployment_slot": self.deployment_slot,
                    "package_version": self.package_version,
                    "rate_package_id": self.rate_package_id,
                    "model_run_id": self.model_run_id,
                    "model_kind": self.model_kind,
                    "monitoring_variant": self.monitoring_variant,
                    "manifest_id": self.manifest_id,
                    "baseline_data_as_of_date": self.baseline_data_as_of_date,
                    "current_package_version": self.current_package_version,
                    "current_rate_package_id": self.current_rate_package_id,
                    "current_deployment_id": self.current_deployment_id,
                    "current_manifest_id": self.current_manifest_id,
                    "current_data_as_of_date": self.current_data_as_of_date,
                }
            ]
        )

    @property
    def metrics(self) -> pd.DataFrame:
        """Recorded metrics with explicit roles, dataset identities, and scopes.

        Monitoring reviews compare the refit with its original baseline scored on
        the same new dataset. That baseline may differ from today's champion.
        Ordinary publication metrics retain their original training/CV scopes.
        """
        return pd.DataFrame(self._metric_rows, columns=_METRIC_COLUMNS)


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _version_rows(connection, engine, *, model_config, model_id, package_version=None):
    schemas = schema_names_from_connectable(engine)
    pricing = schemas.pricing
    monitor = pricing if engine.dialect.name == "sqlite" else schemas.mlops
    slot = model_config.deployment_slot.strip().upper()
    if not slot:
        raise ValueError("deployment_slot is required")
    version_filter = (
        "AND package.package_version=:package_version" if package_version is not None else ""
    )
    rows = (
        connection.execute(
            text(f"""
        SELECT model.model_id, model.model_name, model.target_name, model.model_type,
               package.package_version, package.rate_package_id, run.model_run_id,
               run.model_version, run.model_kind, run.manifest_id,
               recipe.recipe_revision AS definition_revision,
               run.created_ts AS published_at,
               CASE WHEN deployment.rate_package_id=package.rate_package_id THEN 'CHAMPION'
                    WHEN EXISTS (
                        SELECT 1 FROM {pricing}.PRICING_MODEL_DEPLOYMENT AS history
                        WHERE history.model_id=model.model_id
                          AND history.rate_package_id=package.rate_package_id
                          AND history.deployment_slot=:deployment_slot
                          AND history.effective_to_ts IS NOT NULL
                    ) THEN 'FORMER_CHAMPION' ELSE 'CHALLENGER' END AS role,
               CASE observation.variant_code
                   WHEN 'FROZEN_REFIT' THEN 'Coefficients only'
                   WHEN 'REESTIMATE_LAMBDA' THEN 'Coefficients and smoothing'
                   WHEN 'FULL_ADAPTIVE' THEN 'Full refit'
                   ELSE CASE run.model_kind WHEN 'RAW' THEN 'Analyst fit'
                                            WHEN 'ROUTINE_EDIT' THEN 'Grouped fit'
                                            ELSE 'Manual adjustment' END
               END AS refit_type,
               manifest.data_as_of_date,
               observation.variant_code AS monitoring_variant,
               observation.monitor_run_id,
               baseline_manifest.data_as_of_date AS baseline_data_as_of_date,
               deployment.deployment_id AS current_deployment_id,
               deployment.rate_package_id AS current_rate_package_id,
               current_package.package_version AS current_package_version,
               current_run.model_run_id AS current_model_run_id,
               current_run.manifest_id AS current_manifest_id,
               current_manifest.data_as_of_date AS current_data_as_of_date
        FROM {pricing}.PRICING_RATE_PACKAGE AS package
        JOIN {pricing}.PRICING_MODEL AS model ON model.model_id=package.model_id
        JOIN {pricing}.MODEL_RUN AS run
          ON run.rate_package_id=package.rate_package_id AND run.model_id=model.model_id
         AND run.run_status='SUCCESS'
        JOIN {pricing}.DATASET_MANIFEST AS manifest ON manifest.manifest_id=run.manifest_id
        LEFT JOIN {pricing}.MODEL_RECIPE AS recipe
          ON recipe.recipe_id=run.recipe_id AND recipe.model_id=run.model_id
        LEFT JOIN {monitor}.MODEL_MONITOR_PUBLICATION AS publication
          ON publication.model_run_id=run.model_run_id
        LEFT JOIN {monitor}.MODEL_MONITOR_RUN AS observation
          ON observation.monitor_run_id=publication.monitor_run_id
        LEFT JOIN {monitor}.MODEL_FIT_CONTRACT AS contract
          ON contract.fit_contract_id=observation.fit_contract_id
        LEFT JOIN {pricing}.MODEL_RUN AS baseline_run
          ON baseline_run.model_run_id=contract.baseline_model_run_id
        LEFT JOIN {pricing}.DATASET_MANIFEST AS baseline_manifest
          ON baseline_manifest.manifest_id=baseline_run.manifest_id
        LEFT JOIN {pricing}.PRICING_MODEL_DEPLOYMENT AS origin_deployment
          ON origin_deployment.deployment_id=observation.baseline_deployment_id
        LEFT JOIN {pricing}.PRICING_MODEL_DEPLOYMENT AS deployment
          ON deployment.model_id=model.model_id AND deployment.deployment_slot=:deployment_slot
         AND deployment.effective_to_ts IS NULL
        LEFT JOIN {pricing}.PRICING_RATE_PACKAGE AS current_package
          ON current_package.rate_package_id=deployment.rate_package_id
         AND current_package.model_id=model.model_id AND current_package.package_status='PUBLISHED'
        LEFT JOIN {pricing}.MODEL_RUN AS current_run
          ON current_run.rate_package_id=current_package.rate_package_id
         AND current_run.model_id=model.model_id AND current_run.run_status='SUCCESS'
        LEFT JOIN {pricing}.DATASET_MANIFEST AS current_manifest
          ON current_manifest.manifest_id=current_run.manifest_id
        WHERE model.model_id=:model_id AND model.model_name=:model_name
          AND package.package_status='PUBLISHED'
          AND (publication.monitor_run_id IS NULL OR (
              observation.run_status='SUCCESS' AND observation.invariant_status='VERIFIED'
              AND observation.evidence_sealed=1
              AND origin_deployment.deployment_slot=:deployment_slot))
          {version_filter}
        ORDER BY package.package_version DESC
    """),
            {
                "model_id": model_id,
                "model_name": model_config.model_name,
                "deployment_slot": slot,
                "package_version": package_version,
            },
        )
        .mappings()
        .all()
    )
    for row in rows:
        if (
            row["target_name"] != model_config.target_name
            or row["model_type"] != model_config.model_type
        ):
            raise ModelVersionReviewError(
                "SQL model does not match the reviewed model configuration"
            )
        if row["current_deployment_id"] is not None and row["current_manifest_id"] is None:
            raise ModelVersionReviewError(
                "current champion has no successful published model with a manifest"
            )
    return rows


def list_challengers(engine, *, model_config: ModelBuildConfig, model_id: int) -> pd.DataFrame:
    """List saved fits by role and definition revision in the configured slot."""
    model_id = _positive_integer(model_id, "model_id")
    with engine.connect() as connection:
        rows = _version_rows(connection, engine, model_config=model_config, model_id=model_id)
    records = [
        {
            **dict(row),
            "is_current_champion": row["rate_package_id"] == row["current_rate_package_id"],
        }
        for row in rows
    ]
    df = pd.DataFrame(records).rename(columns={"model_version": "fit_version"})
    if df.empty:
        return df
    first = [
        "model_name",
        "role",
        "definition_revision",
        "refit_type",
        "data_as_of_date",
        "published_at",
        "package_version",
    ]
    return df.loc[:, first + [name for name in df.columns if name not in first]]


def review_model_version(
    engine,
    *,
    model_config: ModelBuildConfig,
    model_id: int,
    package_version: int,
) -> ReviewedModelVersion:
    """Read one published version and capture both current champion IDs using SQL only."""
    model_id = _positive_integer(model_id, "model_id")
    package_version = _positive_integer(package_version, "package_version")
    with engine.connect() as connection:
        rows = _version_rows(
            connection,
            engine,
            model_config=model_config,
            model_id=model_id,
            package_version=package_version,
        )
        if len(rows) != 1:
            raise ModelVersionReviewError(
                "selected model version must identify exactly one published package and successful run "
                "in the configured deployment slot"
            )
        row = dict(rows[0])
        metrics = _review_metrics(connection, engine, row)
    row.pop("target_name")
    row.pop("model_type")
    return ReviewedModelVersion(
        engine=engine, model_config=model_config, _metric_rows=tuple(metrics), **row
    )


def _review_metrics(connection, engine, row):
    schemas = schema_names_from_connectable(engine)
    if row["monitor_run_id"] is not None:
        monitor = schemas.pricing if engine.dialect.name == "sqlite" else schemas.mlops
        values = (
            connection.execute(
                text(f"""
            SELECT observation.monitor_run_id, observation.manifest_id,
                   manifest.data_as_of_date, contract.baseline_model_run_id,
                   metric.metric_name, metric.metric_value
            FROM {monitor}.MODEL_MONITOR_RUN AS selected
            JOIN {monitor}.MODEL_MONITOR_RUN AS observation
              ON observation.fit_contract_id=selected.fit_contract_id
             AND observation.baseline_deployment_id=selected.baseline_deployment_id
             AND observation.manifest_id=selected.manifest_id
             AND observation.component_role=selected.component_role
             AND (observation.monitor_run_id=selected.monitor_run_id
                  OR observation.variant_code='STATIC_SCORE')
            JOIN {monitor}.MODEL_MONITOR_METRIC AS metric
              ON metric.monitor_run_id=observation.monitor_run_id
            JOIN {monitor}.MODEL_FIT_CONTRACT AS contract
              ON contract.fit_contract_id=observation.fit_contract_id
            JOIN {schemas.pricing}.DATASET_MANIFEST AS manifest
              ON manifest.manifest_id=observation.manifest_id
            WHERE selected.monitor_run_id=:monitor_run_id
              AND observation.run_status='SUCCESS' AND observation.invariant_status='VERIFIED'
              AND observation.evidence_sealed=1
            ORDER BY observation.variant_code, metric.metric_name
        """),
                {"monitor_run_id": row["monitor_run_id"]},
            )
            .mappings()
            .all()
        )
        return [
            (
                "selected"
                if item["monitor_run_id"] == row["monitor_run_id"]
                else "baseline_at_fit",
                row["model_run_id"]
                if item["monitor_run_id"] == row["monitor_run_id"]
                else item["baseline_model_run_id"],
                item["monitor_run_id"],
                item["manifest_id"],
                item["data_as_of_date"],
                item["metric_name"],
                item["metric_value"],
                "monitoring_snapshot",
            )
            for item in values
        ]
    metrics = []
    for role, prefix in (("selected", ""), ("current_champion", "current_")):
        run_id = row[f"{prefix}model_run_id"]
        if run_id is None:
            continue
        values = (
            connection.execute(
                text(f"""
            SELECT metric_name, metric_value, metric_scope
            FROM {schemas.mlops}.MODEL_RUN_METRIC
            WHERE model_run_id=:model_run_id ORDER BY metric_name
        """),
                {"model_run_id": run_id},
            )
            .mappings()
            .all()
        )
        metrics.extend(
            (
                role,
                run_id,
                None,
                row[f"{prefix}manifest_id"],
                row[f"{prefix}data_as_of_date"],
                item["metric_name"],
                item["metric_value"],
                item["metric_scope"],
            )
            for item in values
        )
    return metrics


def promote_model_version(
    reviewed: ReviewedModelVersion,
    *,
    deployment_reason: str,
    deployed_by: str,
) -> DeploymentResult:
    """Promote the reviewed version without replacing its captured champion IDs."""
    if not isinstance(reviewed, ReviewedModelVersion):
        raise TypeError("reviewed must come from review_model_version")
    refreshed = review_model_version(
        reviewed.engine,
        model_config=reviewed.model_config,
        model_id=reviewed.model_id,
        package_version=reviewed.package_version,
    )
    for name in ("rate_package_id", "model_run_id", "manifest_id", "model_kind", "monitor_run_id"):
        if getattr(refreshed, name) != getattr(reviewed, name):
            raise ModelVersionReviewError("selected SQL model version changed after review")
    return deploy_rate_package(
        reviewed.engine,
        reviewed.model_config,
        rate_package_id=reviewed.rate_package_id,
        expected_current_rate_package_id=reviewed.current_rate_package_id,
        expected_current_deployment_id=reviewed.current_deployment_id,
        deployment_reason=deployment_reason,
        deployed_by=deployed_by,
        model_id=reviewed.model_id,
    )
