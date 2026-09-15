"""Publish one exact refit per sealed monitoring observation, without deployment."""

from __future__ import annotations

import json
import math

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable


class MonitoringPublicationError(ValueError):
    """A challenger does not match its sealed monitoring observation."""


def monitoring_schema(connection):
    schemas = schema_names_from_connectable(connection)
    return schemas.pricing if connection.dialect.name == "sqlite" else schemas.mlops


def _observation(connection, monitor_run_id):
    schema = monitoring_schema(connection)
    row = (
        connection.execute(
            text(f"""SELECT observation.*, contract.baseline_model_run_id, contract.contract_json
            FROM {schema}.MODEL_MONITOR_RUN AS observation
            JOIN {schema}.MODEL_FIT_CONTRACT AS contract
              ON contract.fit_contract_id=observation.fit_contract_id
            WHERE observation.monitor_run_id=:monitor_run_id"""),
            {"monitor_run_id": monitor_run_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise MonitoringPublicationError(
            "monitor_run_id does not identify a monitoring observation"
        )
    if row["variant_code"] not in {"FROZEN_REFIT", "REESTIMATE_LAMBDA", "FULL_ADAPTIVE"}:
        raise MonitoringPublicationError(
            "only monitoring refits can be published; STATIC_SCORE has no challenger"
        )
    if (
        row["run_status"] != "SUCCESS"
        or row["invariant_status"] != "VERIFIED"
        or not row["evidence_sealed"]
    ):
        raise MonitoringPublicationError(
            "monitoring publication requires a successful sealed refit with passing invariants"
        )
    return dict(row)


def validate_monitoring_publication(connection, build):
    """Verify the sealed observation and build identity within the publication transaction."""
    from pricing_pipeline.publishing.recipes import validate_inherited_recipe

    if build.monitor_run_id is None:
        return None
    row = _observation(connection, build.monitor_run_id)
    for name in ("model_id", "manifest_id", "model_frame_sha256"):
        if str(row[name]) != str(getattr(build, name)):
            raise MonitoringPublicationError(
                f"monitoring publication {name} does not match its observation"
            )
    validate_inherited_recipe(
        connection, model_run_id=row["baseline_model_run_id"], capture=build.recipe_capture
    )
    return row


def validate_export_monitoring_link(connection, build, model_run_id):
    """An export retry may neither add nor remove a monitoring identity."""
    row = connection.execute(
        text(
            f"SELECT monitor_run_id FROM {monitoring_schema(connection)}.MODEL_MONITOR_PUBLICATION WHERE model_run_id=:run"
        ),
        {"run": model_run_id},
    ).scalar_one_or_none()
    if (None if row is None else str(row)) != build.monitor_run_id:
        raise MonitoringPublicationError("export retry has a different monitor_run_id linkage")


def _captured_baseline(connection, model_run_id):
    from pricing_pipeline.modeling.monitoring.snapshot import restore_monitoring_snapshot
    from pricing_pipeline.modeling.monitoring.storage import _stored_row, _verify_stored_row

    row = _stored_row(connection, model_run_id)
    if row is None or row["capture_status"] != "CAPTURED":
        raise MonitoringPublicationError("monitoring publication requires a CAPTURED SQL baseline")
    _verify_stored_row(connection, row)
    return restore_monitoring_snapshot(row["snapshot_json"], expected_sha256=row["snapshot_sha256"])


def _validate_fitted_evidence(connection, observation, baseline):
    """Compare captured fit evidence with the sealed monitoring result before linking."""
    schema = monitoring_schema(connection)
    params = {"run": observation["monitor_run_id"]}
    terms = (
        connection.execute(
            text(
                f"SELECT term_name, term_kind, sequence_no, term_structure_sha256, term_metadata_json FROM {schema}.MODEL_MONITOR_TERM WHERE monitor_run_id=:run"
            ),
            params,
        )
        .mappings()
        .all()
    )
    expected_terms = {
        (
            row["term_name"],
            row["term_kind"],
            row["sequence_no"],
            row["term_structure_sha256"],
            row["term_metadata_json"],
        )
        for row in terms
    }
    actual_terms = {
        (row.term_name, row.term_kind, row.sequence_no, row.structure_sha256, row.metadata_json)
        for row in baseline.terms
    }
    if actual_terms != expected_terms:
        raise MonitoringPublicationError(
            "published terms do not match sealed monitoring fit evidence"
        )
    lambdas = (
        connection.execute(
            text(
                f"SELECT component_name, term_name, lambda_value FROM {schema}.MODEL_MONITOR_LAMBDA WHERE monitor_run_id=:run"
            ),
            params,
        )
        .mappings()
        .all()
    )
    expected_lambdas = {
        (row["component_name"], row["term_name"]): row["lambda_value"] for row in lambdas
    }
    actual_lambdas = {
        (row.component_name, row.term_name): row.lambda_value for row in baseline.lambdas
    }
    if actual_lambdas != expected_lambdas:
        raise MonitoringPublicationError(
            "published lambdas do not match sealed monitoring fit evidence"
        )
    relativities = (
        connection.execute(
            text(
                f"SELECT term_name, point_key, log_relativity FROM {schema}.MODEL_MONITOR_RELATIVITY WHERE monitor_run_id=:run"
            ),
            params,
        )
        .mappings()
        .all()
    )
    expected = {
        (row["term_name"], row["point_key"]): float(row["log_relativity"]) for row in relativities
    }
    grid = json.loads(observation["contract_json"])["evaluation_grid"]
    actual = {
        (row.term_name, row.point_key): row.log_relativity for row in baseline.relativities(grid)
    }
    if actual.keys() != expected.keys() or any(
        not math.isclose(value, expected[key], rel_tol=1e-10, abs_tol=1e-11)
        for key, value in actual.items()
    ):
        raise MonitoringPublicationError(
            "published coefficients do not match sealed monitoring fit evidence"
        )


def save_monitoring_publication(connection, *, build, model_run_id):
    """Insert the immutable link after capturing and verifying the exact fitted result."""
    observation = validate_monitoring_publication(connection, build)
    if observation is None:
        return
    if str(model_run_id) == str(observation["baseline_model_run_id"]):
        raise MonitoringPublicationError(
            "monitoring fit evidence requires a separate challenger model run"
        )
    baseline = _captured_baseline(connection, model_run_id)
    _validate_fitted_evidence(connection, observation, baseline)
    schema = monitoring_schema(connection)
    existing = connection.execute(
        text(
            f"SELECT model_run_id FROM {schema}.MODEL_MONITOR_PUBLICATION WHERE monitor_run_id=:monitor"
        ),
        {"monitor": build.monitor_run_id},
    ).scalar_one_or_none()
    if existing is not None:
        if str(existing) != str(model_run_id):
            raise MonitoringPublicationError(
                "monitoring observation already has another publication"
            )
        return
    connection.execute(
        text(
            f"INSERT INTO {schema}.MODEL_MONITOR_PUBLICATION (monitor_run_id, model_run_id, created_by) VALUES (:monitor,:run,:creator)"
        ),
        {"monitor": build.monitor_run_id, "run": model_run_id, "creator": build.created_by},
    )


def _find_monitoring_publication(connection, monitor_run_id):
    observation = _observation(connection, monitor_run_id)
    schemas = schema_names_from_connectable(connection)
    row = (
        connection.execute(
            text(f"""SELECT mr.model_run_id, mr.model_id, pm.model_name, mr.model_version,
                mr.manifest_id, mr.export_id, mr.rate_package_id, mr.run_status,
                mr.rating_workbook_path, mr.mlflow_run_id, mr.publication_receipt_path,
                mr.publication_receipt_sha256, mr.model_kind, mr.model_equivalence_sha256,
                mr.recipe_status, rp.package_version, rp.package_status, rp.parent_rate_package_id,
                recipe.recipe_revision, recipe.recipe_sha256
            FROM {monitoring_schema(connection)}.MODEL_MONITOR_PUBLICATION AS link
            JOIN {schemas.pricing}.MODEL_RUN AS mr ON mr.model_run_id=link.model_run_id
            JOIN {schemas.pricing}.PRICING_RATE_PACKAGE AS rp ON rp.rate_package_id=mr.rate_package_id
            JOIN {schemas.pricing}.PRICING_MODEL AS pm ON pm.model_id=mr.model_id
            LEFT JOIN {schemas.pricing}.MODEL_RECIPE AS recipe ON recipe.recipe_id=mr.recipe_id AND recipe.model_id=mr.model_id
            WHERE link.monitor_run_id=:monitor"""),
            {"monitor": monitor_run_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    valid_status = (
        {"LOCAL_AUDIT", "PUBLISHED"} if connection.dialect.name == "sqlite" else {"PUBLISHED"}
    )
    if (
        row["run_status"] != "SUCCESS"
        or row["package_status"] not in valid_status
        or str(row["model_run_id"]) == str(observation["baseline_model_run_id"])
        or any(str(row[name]) != str(observation[name]) for name in ("model_id", "manifest_id"))
    ):
        raise MonitoringPublicationError(
            "monitoring publication has inconsistent model/manifest/status lineage"
        )
    baseline = _captured_baseline(connection, row["model_run_id"])
    _validate_fitted_evidence(connection, observation, baseline)
    return {
        **row,
        "split_set_id": baseline.payload()["bundle_identity"]["split_set_id"],
        "monitor_run_id": str(monitor_run_id),
        "baseline_model_run_id": observation["baseline_model_run_id"],
        "variant_code": observation["variant_code"],
    }


def find_monitoring_publication(engine, monitor_run_id):
    """Load a verified exact publication using SQL only, or return None before publication."""
    with engine.connect() as connection:
        return _find_monitoring_publication(connection, monitor_run_id)


def reuse_monitoring_publication(connection, build):
    """Reuse only this observation's publication; rounded rating equivalence is irrelevant."""
    if validate_monitoring_publication(connection, build) is None:
        return None
    row = _find_monitoring_publication(connection, build.monitor_run_id)
    if row is None:
        return None
    from pricing_pipeline.publishing.publish import CompletedModelPublishResult

    fields = (
        "model_id",
        "model_name",
        "model_version",
        "manifest_id",
        "split_set_id",
        "export_id",
        "rate_package_id",
        "package_version",
        "package_status",
        "rating_workbook_path",
        "model_run_id",
        "mlflow_run_id",
        "publication_receipt_path",
        "publication_receipt_sha256",
        "model_kind",
        "model_equivalence_sha256",
        "recipe_revision",
        "recipe_sha256",
        "recipe_status",
    )
    return CompletedModelPublishResult(
        **{key: row[key] for key in fields}, was_existing=True, deduplicated=False
    )
