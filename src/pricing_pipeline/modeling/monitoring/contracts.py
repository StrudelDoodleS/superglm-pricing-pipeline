"""Records, variant policies and canonical values used by monitoring.

The workflow produces MonitoringFitResult; persistence verifies and saves it.
Model reconstruction and SQL operations live in their own modules."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd
from superglm import SuperGLM

FIT_CONTRACT_SCHEMA = "superglm_monitoring_fit_contract"


FIT_CONTRACT_SCHEMA_VERSION = 1


INVARIANT_EVIDENCE_SCHEMA = "superglm_monitoring_invariant_evidence"


INVARIANT_EVIDENCE_SCHEMA_VERSION = 1


RESULT_EVIDENCE_SCHEMA = "superglm_monitoring_result_evidence"


RESULT_EVIDENCE_SCHEMA_VERSION = 1


PRIVATE_SUPERGLM_MONITORING_API = "SuperGLM._config/_specs plus fitted spline and categorical state"


class MonitoringError(RuntimeError):
    """Raised when a monitoring contract, refit, or persistence write is unsafe."""


class MonitoringVariant(StrEnum):
    """Select which baseline parameters a monitoring comparison may re-estimate."""

    STATIC_SCORE = "STATIC_SCORE"
    FROZEN_REFIT = "FROZEN_REFIT"
    REESTIMATE_LAMBDA = "REESTIMATE_LAMBDA"
    FULL_ADAPTIVE = "FULL_ADAPTIVE"


@dataclass(frozen=True)
class MonitoringVariantPolicy:
    """The coefficient, lambda and knot changes permitted by one monitoring variant."""

    refit_coefficients: bool
    reestimate_lambdas: bool
    reposition_data_driven_knots: bool


MONITORING_VARIANT_POLICIES: Mapping[MonitoringVariant, MonitoringVariantPolicy] = MappingProxyType(
    {
        MonitoringVariant.STATIC_SCORE: MonitoringVariantPolicy(False, False, False),
        MonitoringVariant.FROZEN_REFIT: MonitoringVariantPolicy(True, False, False),
        MonitoringVariant.REESTIMATE_LAMBDA: MonitoringVariantPolicy(True, True, False),
        MonitoringVariant.FULL_ADAPTIVE: MonitoringVariantPolicy(True, True, True),
    }
)


@dataclass(frozen=True)
class ModelFitContract:
    """Canonical baseline structure and smoothing settings used to check monitoring refits."""

    contract_json: str
    contract_sha256: str
    structure_sha256: str
    superglm_version: str

    def payload(self) -> dict[str, Any]:
        """Return a new mutable decoding of the immutable canonical JSON."""
        return json.loads(self.contract_json)


@dataclass(frozen=True)
class MonitoringTerm:
    """One baseline or refitted term recorded in monitoring evidence."""

    term_name: str
    term_kind: str
    sequence_no: int
    metadata_json: str
    structure_sha256: str


@dataclass(frozen=True)
class MonitoringLambda:
    """One smoothing parameter and its policy recorded for a monitoring term."""

    term_name: str | None
    component_name: str
    lambda_value: float
    lambda_mode: str


@dataclass(frozen=True)
class MonitoringRelativity:
    """A monitoring relativity at one recorded feature level or evaluation point."""

    term_name: str
    term_kind: str
    point_key: str
    point_label: str | None
    point_numeric: float | None
    relativity: float
    log_relativity: float
    is_reference: bool


@dataclass(frozen=True)
class MonitoringInvariantEvidence:
    """Canonical checks showing which baseline properties a monitoring variant preserved."""

    status: str
    evidence_json: str
    evidence_sha256: str

    def payload(self) -> dict[str, Any]:
        """Return a new mutable decoding of the canonical evidence JSON."""
        return json.loads(self.evidence_json)


@dataclass(frozen=True)
class MonitoringFitResult:
    """The refitted/scored model and extracted evidence passed to monitoring persistence."""

    variant: MonitoringVariant
    contract: ModelFitContract
    fitted_model: SuperGLM
    terms: tuple[MonitoringTerm, ...]
    lambdas: tuple[MonitoringLambda, ...]
    relativities: tuple[MonitoringRelativity, ...]
    metrics: Mapping[str, float]
    invariant_evidence: MonitoringInvariantEvidence
    model_frame_sha256: str | None
    fit_configuration_json: str
    result_evidence_sha256: str


@dataclass(frozen=True)
class PersistedMonitoringRun:
    """Saved monitoring identity and whether an identical observation was reused."""

    monitor_run_id: str
    fit_contract_id: str
    run_signature_sha256: str
    deduplicated: bool


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, str | bool):
        return value
    if type(value) is int:
        return value
    if isinstance(value, int | np.integer):
        return int(value)
    if isinstance(value, float | np.floating):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise MonitoringError("monitoring evidence contains a non-finite number")
        return numeric
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, pd.Series | pd.Index):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    raise MonitoringError(f"unsupported monitoring evidence value: {type(value).__name__}")


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        _json_value(payload),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _categorical_scalar_identity(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool | np.bool_):
        return {"type": "boolean", "value": bool(value)}
    if isinstance(value, int | np.integer):
        return {"type": "integer", "value": int(value)}
    if isinstance(value, float | np.floating):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise MonitoringError("categorical real level must be finite")
        return {"type": "real", "value": 0.0 if numeric == 0.0 else numeric}
    if isinstance(value, str | np.str_):
        return {"type": "string", "value": str(value)}
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            raise MonitoringError("categorical timestamp level must not be missing")
        return {"type": "timestamp", "value": value.isoformat()}
    raise MonitoringError(f"unsupported categorical level type: {type(value).__qualname__}")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _label_point_key(identity: Any) -> str:
    return "label:" + _sha256_text(_canonical_json(identity))


def _required_sha256(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise MonitoringError(f"{field_name} must be a lowercase SHA-256 digest")
    return value
