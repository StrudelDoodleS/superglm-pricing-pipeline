"""Immutable declared model configuration and exact semantic identity.

The document keeps registration bindings and execution settings for reconstruction.
Its canonical payload excludes those bindings and execution-only settings. It never
contains dataset provenance or learned fitting state.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
from collections.abc import Mapping
from importlib.metadata import version
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_serializer


class RecipeError(ValueError):
    """A malformed, incompatible or inconsistent model recipe."""


class UnsupportedRecipeError(RecipeError):
    """A Python object has no portable recipe codec."""


class FrozenMap(Mapping):
    """Owned immutable mappings that can also cross the joblib boundary."""

    __slots__ = ("_items",)

    def __init__(self, items):
        object.__setattr__(self, "_items", tuple((k, freeze(v)) for k, v in dict(items).items()))

    def __getitem__(self, key):
        for name, value in self._items:
            if name == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (key for key, _ in self._items)

    def __len__(self):
        return len(self._items)

    def __setattr__(self, name, value):
        raise TypeError("recipe mappings are immutable")

    def __reduce__(self):
        return FrozenMap, (dict(self),)

    def __deepcopy__(self, memo):
        return self


def freeze(value: Any, path: str = "recipe") -> Any:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise RecipeError(f"{path}: mapping keys must be strings; use level/value entries")
        return FrozenMap({key: freeze(item, f"{path}.{key}") for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item, f"{path}[{i}]") for i, item in enumerate(value))
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise RecipeError(f"{path}: expected a finite JSON value, got {type(value).__name__}")


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        thaw(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


# Every estimator parameter is classified in the adapter. These affect resource
# use only; solver tolerances, iteration limits and discretization remain semantic.
EXECUTION_PARAMETERS = frozenset({"retain_fit_state"})
BINDING_FIELDS = frozenset({"name", "label", "model_type", "deployment_slot"})


class RecipeDocument(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    format_version: Literal[1] = 1
    name: str
    label: str
    model_type: str
    deployment_slot: str
    target: str
    features: dict[str, Any]
    feature_order: tuple[str, ...] = ()
    estimator: dict[str, Any] = Field(default_factory=dict)
    interactions: tuple[Any, ...] = ()
    transforms: dict[str, Any] = Field(default_factory=dict)
    transform_order: tuple[str, ...] = ()
    validation: dict[str, Any] = Field(
        default_factory=lambda: dict(type="kfold", n_splits=5, shuffle=True, random_state=42)
    )
    groups_column: str | None = None
    scoring: tuple[str, ...] = ("deviance", "nll", "gini")
    fit_mode: Literal["fit", "fit_reml"] = "fit_reml"
    spline_export: Literal["exact", "binned"] = "exact"
    offset_column: str | None = None
    offset_source_column: str | None = None
    offset_label: str | None = None
    sample_weight_column: str | None = None
    export_weight_column: str | None = None

    def __init__(self, **data):
        data = thaw(freeze(data))
        for name in ("feature_order", "transform_order", "scoring", "interactions"):
            if name in data:
                data[name] = tuple(data[name])
        data.setdefault("feature_order", tuple(data.get("features", {})))
        data.setdefault("transform_order", tuple(data.get("transforms", {})))
        try:
            super().__init__(**data)
        except ValidationError as exc:
            raise RecipeError(
                "; ".join(".".join(map(str, e["loc"])) + ": " + e["msg"] for e in exc.errors())
            ) from exc
        for name in ("feature", "transform"):
            order = getattr(self, f"{name}_order")
            mapping = getattr(self, f"{name}s")
            if len(set(order)) != len(order) or set(order) != set(mapping):
                raise RecipeError(f"{name}_order: must list each declared {name} exactly once")
        if not self.features:
            raise RecipeError("features: at least one feature is required")
        for name in (*BINDING_FIELDS, "target"):
            if not getattr(self, name).strip():
                raise RecipeError(f"{name}: must be non-empty")
        # Nested constructor validation and default resolution are supplied by
        # explicit codecs, never by classes imported from a document.
        from .superglm import normalize_document_parts

        parts = normalize_document_parts(self)
        for name, value in parts.items():
            object.__setattr__(self, name, freeze(value, name))

    def to_dict(self) -> dict[str, Any]:
        return {name: thaw(getattr(self, name)) for name in type(self).model_fields}

    @model_serializer
    def _serialize(self):
        return self.to_dict()

    def model_copy(self, *, update=None, deep=False):
        return type(self)(**(self.to_dict() | (update or {})))

    @property
    def canonical_json(self) -> str:
        payload = self.to_dict()
        for field in BINDING_FIELDS:
            payload.pop(field)
        for field in EXECUTION_PARAMETERS:
            payload["estimator"].pop(field, None)
        return canonical_json(payload)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


class RecipeCapture(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)
    status: Literal["CAPTURED", "LEGACY", "UNSUPPORTED"] = "LEGACY"
    document: RecipeDocument | None = None
    canonical: str | None = None
    sha256: str | None = None
    unavailable_reason: str | None = None
    environment: Any = Field(default_factory=dict)

    def __init__(self, **data):
        data.setdefault("environment", {})
        try:
            super().__init__(**data)
        except ValidationError as exc:
            raise RecipeError(str(exc)) from exc
        if self.status == "CAPTURED":
            if self.document is None or self.unavailable_reason is not None:
                raise RecipeError(
                    "recipe capture: CAPTURED requires a document and no unavailable reason"
                )
            if (
                self.canonical != self.document.canonical_json
                or self.sha256 != self.document.sha256
            ):
                raise RecipeError(
                    "recipe capture: canonical content or checksum disagrees with document"
                )
        elif any(value is not None for value in (self.document, self.canonical, self.sha256)):
            raise RecipeError(
                "recipe capture: unavailable recipes cannot contain verified evidence"
            )
        if self.status == "UNSUPPORTED" and not self.unavailable_reason:
            raise RecipeError("recipe capture: UNSUPPORTED requires a reason")
        if self.status == "LEGACY" and self.unavailable_reason is not None:
            raise RecipeError("recipe capture: LEGACY cannot claim an unsupported reason")
        object.__setattr__(self, "environment", freeze(self.environment, "environment"))

    @classmethod
    def captured(cls, document):
        return cls(
            status="CAPTURED",
            document=document,
            canonical=document.canonical_json,
            sha256=document.sha256,
            environment=capture_environment(),
        )

    def to_payload(self):
        return dict(
            status=self.status,
            document=None if self.document is None else self.document.to_dict(),
            canonical=self.canonical,
            sha256=self.sha256,
            unavailable_reason=self.unavailable_reason,
            environment=thaw(self.environment),
        )

    @classmethod
    def from_payload(cls, payload):
        data = thaw(payload)
        if data.get("document") is not None:
            data["document"] = RecipeDocument(**data["document"])
        return cls(**data)


def capture_environment():
    return {
        "python": platform.python_version(),
        "pipeline": version("superglm-pricing-pipeline"),
        "superglm": version("superglm"),
    }
