"""Describe stable model registration and validation split choices.

``ModelBuildConfig`` is the internal registration record.
``ValidationSplitConfig`` is also exposed through the notebook API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationSplitConfig:
    """Declare generated folds or splits already encoded in a dataset column.

    Use ``kfold`` or ``train_test_split`` to generate positions. Use
    ``column_kfold`` or ``column_holdout`` when data already assigns membership.
    A notebook spec can also accept an analyst-supplied splitter directly.
    """

    method: str = "kfold"
    n_splits: int | None = 5
    test_size: float | None = None
    random_state: int | None = 42
    shuffle: bool = True
    stratify_column: str | None = None
    materialize: bool = False
    column: str | None = None
    train_values: tuple[Any, ...] = ()
    test_values: tuple[Any, ...] = ()
    splitter_class: str | None = None
    splitter_params: dict[str, Any] | None = None
    groups_column: str | None = None

    @classmethod
    def kfold(
        cls,
        *,
        n_splits: int = 5,
        random_state: int | None = 42,
        shuffle: bool = True,
        materialize: bool = False,
    ) -> "ValidationSplitConfig":
        """Generate K-fold validation, with optional shuffling and a reproducible seed."""

        return cls(
            method="kfold",
            n_splits=n_splits,
            random_state=random_state if shuffle else None,
            shuffle=shuffle,
            materialize=materialize,
        )

    @classmethod
    def train_test_split(
        cls,
        *,
        test_size: float = 0.2,
        random_state: int | None = 42,
        shuffle: bool = True,
        stratify_column: str | None = None,
        materialize: bool = False,
    ) -> "ValidationSplitConfig":
        """Generate one train/test split, optionally stratified by a data column."""

        return cls(
            method="train_test_split",
            n_splits=None,
            test_size=test_size,
            random_state=random_state,
            shuffle=shuffle,
            stratify_column=stratify_column,
            materialize=materialize,
        )

    @classmethod
    def column_kfold(
        cls,
        *,
        column: str,
        materialize: bool = False,
    ) -> "ValidationSplitConfig":
        """Hold out each distinct column value in turn as a validation fold."""

        return cls(
            method="column_kfold",
            n_splits=None,
            test_size=None,
            random_state=None,
            shuffle=False,
            stratify_column=None,
            materialize=materialize,
            column=column,
        )

    @classmethod
    def column_holdout(
        cls,
        *,
        column: str,
        train_values: tuple[Any, ...],
        test_values: tuple[Any, ...],
        materialize: bool = False,
    ) -> "ValidationSplitConfig":
        """Select training and test rows using explicit values from one column."""

        return cls(
            method="column_holdout",
            n_splits=None,
            test_size=None,
            random_state=None,
            shuffle=False,
            stratify_column=None,
            materialize=materialize,
            column=column,
            train_values=train_values,
            test_values=test_values,
        )


@dataclass(frozen=True)
class ModelBuildConfig:
    """Internal model registration fields and recorded validation configuration.

    ``PricingModelSpec`` supplies this record in the notebook workflow; feature
    constructors and fitted parameters belong to the estimator.
    """

    model_name: str
    model_label: str
    target_name: str
    model_type: str
    deployment_slot: str
    validation_split: ValidationSplitConfig = field(default_factory=ValidationSplitConfig.kfold)
