"""Analyst model choices and the validation of their data-column roles.

PricingModelSpec maps prepared columns to features, target, weights and offset,
and describes transforms, validation and fit/export choices. Notebook workflows
import this record; it does not import or execute those workflows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from pricing_pipeline.data.dataset import PricingDataset
from pricing_pipeline.data.transforms import (
    Transform,
    normalize_transforms,
)
from pricing_pipeline.data.validation import Splitter, splitter_config
from pricing_pipeline.models.config import ValidationSplitConfig


@dataclass(frozen=True)
class PricingModelSpec:
    """Declare which data columns the model uses and how fitting is evaluated.

    Supply a ``PricingDataset`` for source, key and as-at metadata. ``features``
    is an ordered list or tuple of prepared column names; the SuperGLM instance
    supplies their categorical, numeric or spline treatment.

    ``transforms`` maps output names to source-column operations. Prepare the
    fit input with ``apply_transforms(dataset.df, spec.transforms)``. An offset
    column supplies a covariate with coefficient fixed at one; its source and
    label are inferred when that column has a declared transform.

    ``validation`` accepts a split configuration or a splitter with ``split``.
    ``groups_column`` supplies groups to that splitter. ``fit_mode`` defaults
    to ``fit_reml``; ``spline_export`` chooses exact polynomial or binned output.
    Constructing a spec validates these choices without fitting or writing SQL.
    """

    name: str
    label: str
    target: str
    model_type: str
    deployment_slot: str
    features: Sequence[str]
    dataset_name: str | None = None
    source_system: str | None = None
    pk_columns: Sequence[str] | None = None
    validation: ValidationSplitConfig | Splitter = field(
        default_factory=ValidationSplitConfig.kfold
    )
    offset_column: str | None = None
    offset_source_column: str | None = None
    offset_label: str | None = None
    sample_weight_column: str | None = None
    export_weight_column: str | None = None
    data_as_of_column: str | None = None
    scoring: tuple[str, ...] = ("deviance", "nll", "gini")
    fit_mode: str = "fit_reml"
    dataset: PricingDataset | None = None
    transforms: Mapping[str, Transform] = field(default_factory=dict)
    spline_export: str = "exact"
    groups_column: str | None = None

    def __post_init__(self) -> None:
        if self.spline_export not in {"exact", "binned"}:
            raise ValueError("spline_export must be 'exact' or 'binned'")
        if self.dataset is not None:
            if not isinstance(self.dataset, PricingDataset):
                raise TypeError("dataset must be a PricingDataset")
            for name, expected in (
                ("dataset_name", self.dataset.name),
                ("source_system", self.dataset.source),
                ("pk_columns", self.dataset.key),
                ("data_as_of_column", self.dataset.as_of),
            ):
                supplied = getattr(self, name)
                if supplied is not None:
                    if name == "pk_columns":
                        if isinstance(supplied, str) or not isinstance(supplied, Sequence):
                            raise TypeError("pk_columns must be an ordered sequence of names")
                        supplied = tuple(str(value).strip() for value in supplied)
                    else:
                        supplied = str(supplied).strip()
                    if supplied != expected:
                        raise ValueError(f"{name} conflicts with the dataset")
                object.__setattr__(self, name, expected)
        object.__setattr__(self, "transforms", normalize_transforms(self.transforms))
        for name in ("features", "pk_columns"):
            values = getattr(self, name)
            if isinstance(values, str) or not isinstance(values, Sequence):
                raise TypeError(f"{name} must be an ordered sequence of names")
        for field_name in (
            "name",
            "label",
            "target",
            "model_type",
            "dataset_name",
            "source_system",
            "fit_mode",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "deployment_slot",
            _required_text(self.deployment_slot, "deployment_slot").upper(),
        )
        object.__setattr__(
            self,
            "features",
            tuple(_required_text(value, "features") for value in self.features),
        )
        object.__setattr__(
            self,
            "pk_columns",
            tuple(_required_text(value, "pk_columns") for value in self.pk_columns),
        )
        object.__setattr__(
            self,
            "scoring",
            tuple(_required_text(value, "scoring") for value in self.scoring),
        )
        for field_name in (
            "offset_column",
            "offset_source_column",
            "offset_label",
            "sample_weight_column",
            "export_weight_column",
            "data_as_of_column",
            "groups_column",
        ):
            value = getattr(self, field_name)
            object.__setattr__(
                self,
                field_name,
                None if value is None else _required_text(value, field_name),
            )
        if self.offset_column in self.transforms:
            transform = self.transforms[self.offset_column]
            for name, expected in (
                ("offset_source_column", transform.source),
                ("offset_label", transform.expression),
            ):
                supplied = getattr(self, name)
                if supplied is not None and supplied != expected:
                    raise ValueError(f"{name} conflicts with the offset transform")
                object.__setattr__(self, name, expected)
        offset_fields = (
            self.offset_column,
            self.offset_source_column,
            self.offset_label,
        )
        if any(value is not None for value in offset_fields) and not all(
            value is not None for value in offset_fields
        ):
            raise ValueError(
                "offset_column, offset_source_column, and offset_label must be configured together"
            )
        if not self.features:
            raise ValueError("features must contain at least one column")
        if len(set(self.features)) != len(self.features):
            raise ValueError("features must not contain duplicates")
        if not self.pk_columns:
            raise ValueError("pk_columns must contain at least one column")
        if len(set(self.pk_columns)) != len(self.pk_columns):
            raise ValueError("pk_columns must not contain duplicates")
        if not self.scoring:
            raise ValueError("scoring must contain at least one metric")
        if len(set(self.scoring)) != len(self.scoring):
            raise ValueError("scoring must not contain duplicates")
        if isinstance(self.validation, ValidationSplitConfig):
            if self.groups_column is not None:
                raise ValueError("groups_column requires a splitter in validation")
            if self.validation.method not in {
                "none",
                "kfold",
                "train_test_split",
                "column_kfold",
                "column_holdout",
            }:
                raise ValueError(
                    f"validation method {self.validation.method!r} is not supported by "
                    "the notebook workflow; pass a splitter or use a column-based split"
                )
            if self.validation.method != "none" and not self.validation.materialize:
                object.__setattr__(self, "validation", replace(self.validation, materialize=True))
        validation_config = self._validation_config()

        roles: dict[str, list[str]] = {}
        role_values = {
            "target": (self.target,),
            "primary key": self.pk_columns,
            "feature": self.features,
            "split": (validation_config.column,),
            "offset": (self.offset_column,),
            "offset source": (self.offset_source_column,),
            "sample weight": (self.sample_weight_column,),
            "export weight": (self.export_weight_column,),
            "data as of": (self.data_as_of_column,),
        }
        for role, columns in role_values.items():
            for column in columns:
                if column is not None:
                    roles.setdefault(column, []).append(role)
        structural_roles = {
            "target",
            "primary key",
            "feature",
            "split",
            "data as of",
        }
        overlaps = {
            column: assigned_roles
            for column, assigned_roles in roles.items()
            if len(assigned_roles) > 1 and any(role in structural_roles for role in assigned_roles)
        }
        if overlaps:
            detail = "; ".join(
                f"{column}={','.join(assigned_roles)}"
                for column, assigned_roles in sorted(overlaps.items())
            )
            raise ValueError(f"model column roles overlap: {detail}")

    def _validation_config(self) -> ValidationSplitConfig:
        if isinstance(self.validation, ValidationSplitConfig):
            return self.validation
        return splitter_config(self.validation, groups_column=self.groups_column)


def _required_text(value: Any, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned
