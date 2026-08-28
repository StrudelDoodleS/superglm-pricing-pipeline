"""Persist model-run, dataset, split, metric, and parent lineage evidence."""

from __future__ import annotations

from contextlib import nullcontext

from sqlalchemy import text
from sqlalchemy.engine import Engine

from pricing_pipeline.models.spec import ApprovedModelBuild


class ModelRunIdentityError(RuntimeError):
    """Raised when a successful model-run identity is reused inconsistently."""


_DATASET_ROLE = "training"
_SPLIT_ROLE = "validation"


def record_model_run(
    engine: Engine | None,
    *,
    build: ApprovedModelBuild,
    dag_id: str,
    airflow_run_id: str,
    rate_package_id: int | None,
    parent_model_run_id: int | None = None,
    connection=None,
) -> int:
    manifest_id = build.manifest_id
    split_set_id = build.split_set_id
    metrics = build.metrics
    metric_scopes = build.metric_scopes
    fold_metrics = build.fold_metrics
    if fold_metrics and split_set_id is None:
        raise ValueError("fold_metrics require split_set_id")
    params = {
        "dag_id": dag_id,
        "airflow_run_id": airflow_run_id,
        "mlflow_run_id": build.mlflow_run_id,
        "manifest_id": manifest_id,
        "split_set_id": split_set_id,
        "export_id": build.export_id,
        "model_id": build.model_id,
        "model_name": build.model_name,
        "model_version": build.model_version,
        "model_kind": build.model_kind,
        "model_equivalence_sha256": build.model_equivalence_sha256,
        "rate_package_id": rate_package_id,
        "rating_workbook_path": build.rating_workbook_path,
        "rating_workbook_sha256": build.rating_workbook_sha256,
        "run_status": "SUCCESS",
        "created_by": build.created_by,
        "publication_receipt_path": build.publication_receipt_path,
        "publication_receipt_sha256": build.publication_receipt_sha256,
        "candidate_artifact_path": build.candidate_artifact_path,
        "candidate_artifact_sha256": build.candidate_artifact_sha256,
        "candidate_artifact_format": build.candidate_artifact_format,
        "candidate_artifact_size_bytes": build.candidate_artifact_size_bytes,
        "candidate_python_version": build.candidate_python_version,
        "candidate_superglm_version": build.candidate_superglm_version,
        "model_source_sha256": build.model_source_sha256,
        "dataset_role": _DATASET_ROLE,
        "split_role": _SPLIT_ROLE,
        "parent_model_run_id": parent_model_run_id,
    }
    transaction = engine.begin() if connection is None else nullcontext(connection)
    with transaction as con:
        if parent_model_run_id is not None:
            parent_matches_package = con.execute(
                text(
                    """
                    SELECT TOP (1) 1
                    FROM pricing.PRICING_RATE_PACKAGE AS child_package
                        WITH (UPDLOCK, HOLDLOCK)
                    JOIN pricing.MODEL_RUN AS parent_run
                        WITH (UPDLOCK, HOLDLOCK)
                      ON parent_run.model_run_id = :parent_model_run_id
                     AND parent_run.rate_package_id = child_package.parent_rate_package_id
                    WHERE child_package.rate_package_id = :rate_package_id
                      AND child_package.model_id = :model_id
                      AND parent_run.model_id = :model_id
                      AND parent_run.run_status = 'SUCCESS'
                    """
                ),
                params,
            ).scalar_one_or_none()
            if parent_matches_package is None:
                raise ModelRunIdentityError(
                    "parent_model_run_id does not match the package parent, model, "
                    "or a successful parent run"
                )

        con.execute(
            text(
                """
                INSERT INTO pricing.MODEL_RUN (
                    dag_id, airflow_run_id, mlflow_run_id, manifest_id, export_id,
                    model_id, model_name, model_version, model_kind,
                    model_equivalence_sha256, rate_package_id, rating_workbook_path,
                    rating_workbook_sha256, publication_receipt_path,
                    publication_receipt_sha256, candidate_artifact_path,
                    candidate_artifact_sha256, candidate_artifact_format,
                    candidate_artifact_size_bytes, candidate_python_version,
                    candidate_superglm_version, model_source_sha256,
                    parent_model_run_id, run_status, completed_ts, created_by
                ) VALUES (
                    :dag_id, :airflow_run_id, :mlflow_run_id, :manifest_id, :export_id,
                    :model_id, :model_name, :model_version, :model_kind,
                    :model_equivalence_sha256, :rate_package_id, :rating_workbook_path,
                    :rating_workbook_sha256, :publication_receipt_path,
                    :publication_receipt_sha256, :candidate_artifact_path,
                    :candidate_artifact_sha256, :candidate_artifact_format,
                    :candidate_artifact_size_bytes, :candidate_python_version,
                    :candidate_superglm_version, :model_source_sha256,
                    :parent_model_run_id, :run_status, SYSUTCDATETIME(), :created_by
                )
                """
            ),
            params,
        )
        model_run_id = con.execute(
            text(
                """
                SELECT model_run_id FROM pricing.MODEL_RUN
                WHERE dag_id = :dag_id
                  AND airflow_run_id = :airflow_run_id
                  AND model_id = :model_id
                """
            ),
            params,
        ).scalar_one()
        link_params = {
            "model_run_id": model_run_id,
            "manifest_id": manifest_id,
            "split_set_id": split_set_id,
            "dataset_role": _DATASET_ROLE,
            "split_role": _SPLIT_ROLE,
            "parent_model_run_id": parent_model_run_id,
        }
        con.execute(
            text(
                """
                INSERT INTO mlops.MODEL_RUN_DATASET (
                    model_run_id, manifest_id, dataset_role
                ) VALUES (:model_run_id, :manifest_id, :dataset_role)
                """
            ),
            link_params,
        )
        if split_set_id is not None:
            con.execute(
                text(
                    """
                    INSERT INTO mlops.MODEL_RUN_SPLIT_SET (
                        model_run_id, manifest_id, split_set_id, dataset_role, split_role
                    ) VALUES (
                        :model_run_id, :manifest_id, :split_set_id,
                        :dataset_role, :split_role
                    )
                    """
                ),
                link_params,
            )
        if parent_model_run_id is not None:
            con.execute(
                text(
                    """
                    INSERT INTO mlops.MODEL_RUN_DATASET (
                        model_run_id, manifest_id, dataset_role
                    )
                    SELECT :model_run_id, parent.manifest_id, parent.dataset_role
                    FROM mlops.MODEL_RUN_DATASET AS parent
                    WHERE parent.model_run_id = :parent_model_run_id
                      AND NOT EXISTS (
                          SELECT 1 FROM mlops.MODEL_RUN_DATASET AS current_link
                          WHERE current_link.model_run_id = :model_run_id
                            AND current_link.manifest_id = parent.manifest_id
                            AND current_link.dataset_role = parent.dataset_role
                      )
                    """
                ),
                link_params,
            )
            con.execute(
                text(
                    """
                    INSERT INTO mlops.MODEL_RUN_SPLIT_SET (
                        model_run_id, manifest_id, split_set_id, dataset_role, split_role
                    )
                    SELECT :model_run_id, parent.manifest_id, parent.split_set_id,
                           parent.dataset_role, parent.split_role
                    FROM mlops.MODEL_RUN_SPLIT_SET AS parent
                    WHERE parent.model_run_id = :parent_model_run_id
                      AND NOT EXISTS (
                          SELECT 1 FROM mlops.MODEL_RUN_SPLIT_SET AS current_link
                          WHERE current_link.model_run_id = :model_run_id
                            AND current_link.split_set_id = parent.split_set_id
                            AND current_link.split_role = parent.split_role
                      )
                    """
                ),
                link_params,
            )
        for metric_name in sorted(metrics):
            con.execute(
                text(
                    """
                    INSERT INTO mlops.MODEL_RUN_METRIC (
                        model_run_id, metric_name, metric_value, metric_scope
                    ) VALUES (
                        :model_run_id, :metric_name, :metric_value, :metric_scope
                    )
                    """
                ),
                {
                    "model_run_id": model_run_id,
                    "metric_name": metric_name,
                    "metric_value": float(metrics[metric_name]),
                    "metric_scope": metric_scopes.get(metric_name),
                },
            )
        for metric in fold_metrics:
            con.execute(
                text(
                    """
                    INSERT INTO pricing.CV_FOLD_METRIC (
                        model_run_id, split_set_id, fold_no, metric_name, metric_value
                    ) VALUES (
                        :model_run_id, :split_set_id, :fold_no,
                        :metric_name, :metric_value
                    )
                    """
                ),
                {
                    "model_run_id": model_run_id,
                    "split_set_id": split_set_id,
                    "fold_no": int(metric["fold_no"]),
                    "metric_name": str(metric["metric_name"]),
                    "metric_value": float(metric["metric_value"]),
                },
            )
    return int(model_run_id)


__all__ = ["ModelRunIdentityError", "record_model_run"]
