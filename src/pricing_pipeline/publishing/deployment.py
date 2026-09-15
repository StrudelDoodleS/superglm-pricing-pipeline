"""Activate a published rating package in a model's deployment slot.

Check package eligibility and the deployment snapshot reviewed by the caller
before changing the active package. Saving a model does not call this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import text

from pricing_pipeline.models.config import ModelBuildConfig


@dataclass(frozen=True)
class DeploymentResult:
    """The activated package and the package it replaced, with the recorded deployment reason."""

    model_id: int
    deployment_slot: str
    previous_rate_package_id: int | None
    rate_package_id: int
    package_version: int
    deployed_by: str
    deployment_reason: str


_DEPLOYMENT_LOCK_TIMEOUT_MS = 10_000
_UNSPECIFIED_DEPLOYMENT_ID = object()


class DeploymentError(RuntimeError):
    """Raised when a rate package cannot be deployed."""


class StaleChampionError(DeploymentError):
    """Raised when the active champion changed after deployment approval."""


def deploy_rate_package(
    engine,
    config: ModelBuildConfig,
    *,
    rate_package_id: int,
    expected_current_rate_package_id: int | None,
    deployment_reason: str,
    deployed_by: str,
    model_id: int,
    expected_current_deployment_id: int | None | object = _UNSPECIFIED_DEPLOYMENT_ID,
) -> DeploymentResult:
    """Deploy using the reviewed package and, when supplied, deployment identity.

    Omitting the deployment ID retains the historical package-only comparison.
    Passing None explicitly requires that no champion deployment exists.
    """
    deployment_reason = _required_text(deployment_reason, "deployment_reason")
    deployed_by = _required_text(deployed_by, "deployed_by")
    slot = _required_text(config.deployment_slot, "deployment_slot").upper()

    with engine.begin() as con:
        _acquire_deployment_lock(con, model_id=model_id, deployment_slot=slot)

        package = _resolve_package(
            con,
            rate_package_id=rate_package_id,
        )

        if int(package["model_id"]) != int(model_id):
            raise DeploymentError("rate package model_id does not match deployment model_id")
        if package["package_status"] != "PUBLISHED":
            raise DeploymentError("only PUBLISHED rate packages can be deployed")

        current = _current_deployment(con, model_id=model_id, deployment_slot=slot)
        previous_rate_package_id = int(current["rate_package_id"]) if current is not None else None
        resolved_rate_package_id = int(package["rate_package_id"])
        if previous_rate_package_id != expected_current_rate_package_id:
            raise StaleChampionError(
                "deployment approval is stale: expected current "
                f"rate_package_id={expected_current_rate_package_id}, "
                f"found {previous_rate_package_id}"
            )
        if expected_current_deployment_id is not _UNSPECIFIED_DEPLOYMENT_ID:
            current_deployment_id = int(current["deployment_id"]) if current is not None else None
            if current_deployment_id != expected_current_deployment_id:
                raise StaleChampionError(
                    "deployment approval is stale: expected current "
                    f"deployment_id={expected_current_deployment_id}, "
                    f"found {current_deployment_id}"
                )
        if previous_rate_package_id == resolved_rate_package_id:
            return DeploymentResult(
                model_id=int(model_id),
                deployment_slot=slot,
                previous_rate_package_id=previous_rate_package_id,
                rate_package_id=resolved_rate_package_id,
                package_version=int(package["package_version"]),
                deployed_by=str(current["deployed_by"]),
                deployment_reason=str(current["deployment_note"]),
            )

        transition_ts = con.execute(
            text("SELECT CAST(SYSUTCDATETIME() AS DATETIME2(3))")
        ).scalar_one()
        if current is not None:
            # DATETIME2(3) intervals must have positive length, even within one clock tick.
            transition_ts = max(
                transition_ts,
                current["effective_from_ts"] + timedelta(milliseconds=1),
            )

        con.execute(
            text("""
            UPDATE pricing.PRICING_MODEL_DEPLOYMENT
            SET effective_to_ts = :transition_ts
            WHERE model_id = :model_id
              AND deployment_slot = :deployment_slot
              AND effective_to_ts IS NULL;
        """),
            {
                "model_id": model_id,
                "deployment_slot": slot,
                "transition_ts": transition_ts,
            },
        )

        con.execute(
            text("""
            INSERT INTO pricing.PRICING_MODEL_DEPLOYMENT (
                model_id,
                rate_package_id,
                deployment_slot,
                effective_from_ts,
                deployed_by,
                deployment_note
            )
            VALUES (
                :model_id,
                :rate_package_id,
                :deployment_slot,
                :transition_ts,
                :deployed_by,
                :deployment_note
            );
        """),
            {
                "model_id": model_id,
                "rate_package_id": resolved_rate_package_id,
                "deployment_slot": slot,
                "transition_ts": transition_ts,
                "deployed_by": deployed_by,
                "deployment_note": deployment_reason,
            },
        )

    return DeploymentResult(
        model_id=int(model_id),
        deployment_slot=slot,
        previous_rate_package_id=previous_rate_package_id,
        rate_package_id=resolved_rate_package_id,
        package_version=int(package["package_version"]),
        deployed_by=deployed_by,
        deployment_reason=deployment_reason,
    )


def _required_text(value: str | None, field_name: str) -> str:
    if value is None:
        raise DeploymentError(f"{field_name} is required")
    cleaned = value.strip()
    if not cleaned:
        raise DeploymentError(f"{field_name} is required")
    return cleaned


def _acquire_deployment_lock(con, *, model_id: int, deployment_slot: str) -> None:
    lock_resource = f"pricing_model_deployment:{int(model_id)}:{deployment_slot}"
    lock_result = con.execute(
        text("""
        DECLARE @lock_result INT;
        EXEC @lock_result = sys.sp_getapplock
            @Resource = :lock_resource,
            @LockMode = 'Exclusive',
            @LockOwner = 'Transaction',
            @LockTimeout = :lock_timeout_ms;
        SELECT @lock_result;
    """),
        {
            "lock_resource": lock_resource,
            "lock_timeout_ms": _DEPLOYMENT_LOCK_TIMEOUT_MS,
        },
    ).scalar_one()
    if int(lock_result) < 0:
        raise DeploymentError(
            f"could not acquire deployment lock for model_id={model_id} "
            f"deployment_slot={deployment_slot!r}",
        )


def _resolve_package(
    con,
    *,
    rate_package_id: int,
) -> dict[str, Any]:
    row = (
        con.execute(
            text("""
        SELECT
            rate_package_id,
            model_id,
            package_version,
            package_status
        FROM pricing.PRICING_RATE_PACKAGE
        WHERE rate_package_id = :rate_package_id
    """),
            {"rate_package_id": rate_package_id},
        )
        .mappings()
        .one_or_none()
    )

    if row is None:
        raise DeploymentError("rate package not found")
    return dict(row)


def _current_deployment(con, *, model_id: int, deployment_slot: str) -> dict[str, Any] | None:
    row = (
        con.execute(
            text("""
        SELECT
            deployment_id,
            rate_package_id,
            effective_from_ts,
            deployed_by,
            COALESCE(deployment_note, '') AS deployment_note
        FROM pricing.PRICING_MODEL_DEPLOYMENT
        WHERE model_id = :model_id
          AND deployment_slot = :deployment_slot
          AND effective_to_ts IS NULL
    """),
            {
                "model_id": model_id,
                "deployment_slot": deployment_slot,
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return dict(row)
