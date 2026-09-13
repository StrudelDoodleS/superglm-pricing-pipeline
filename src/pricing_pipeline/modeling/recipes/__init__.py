"""Portable declared recipes with no database or fitting side effects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import io
from .schema import RecipeCapture, RecipeDocument, RecipeError, UnsupportedRecipeError
from .superglm import (
    decode_estimator,
    decode_transforms,
    decode_validation,
    encode_estimator,
    encode_transforms,
    encode_validation,
)

if TYPE_CHECKING:
    from pathlib import Path

    from superglm import SuperGLM

    from pricing_pipeline.data.dataset import PricingDataset
    from pricing_pipeline.notebook import PricingModelSpec


@dataclass(frozen=True)
class ModelRecipe:
    """An immutable model definition that can be saved as editable TOML.

    Capture declared choices with ``from_model(model, spec=spec)`` or export a
    verified fitted candidate's ``recipe``. ``load(path).build(dataset=dataset)``
    returns a matching spec and an unfitted SuperGLM instance.
    """

    document: RecipeDocument

    @classmethod
    def from_model(cls, model: SuperGLM, *, spec: PricingModelSpec) -> ModelRecipe:
        """Capture the estimator's declared constructors and the spec's column roles.

        Learned coefficients and fitting state are excluded. Unsupported custom
        objects raise ``UnsupportedRecipeError`` rather than producing partial TOML.
        """

        estimator, features, interactions = encode_estimator(model)
        if tuple(features) != tuple(spec.features):
            raise RecipeError(
                "features: estimator feature order must match PricingModelSpec.features"
            )
        fields = (
            "name",
            "label",
            "model_type",
            "deployment_slot",
            "target",
            "groups_column",
            "scoring",
            "fit_mode",
            "spline_export",
            "offset_column",
            "offset_source_column",
            "offset_label",
            "sample_weight_column",
            "export_weight_column",
        )
        return cls(
            RecipeDocument(
                **{name: getattr(spec, name) for name in fields},
                features=features,
                estimator=estimator,
                interactions=interactions,
                transforms=encode_transforms(spec.transforms),
                validation=encode_validation(spec.validation),
            )
        )

    @classmethod
    def load(cls, path: str | Path) -> ModelRecipe:
        """Read and validate a TOML recipe without fitting or opening a database."""

        return cls(io.load(path))

    def save(self, path: str | Path, *, replace: bool = False) -> Path:
        """Write editable TOML and return its path.

        An existing file requires ``replace=True``. The saved file contains declared
        model choices; SQL assigns its recipe revision when a fitted build is saved.
        """

        return io.save(self.document, path, replace=replace)

    def build(self, *, dataset: PricingDataset) -> tuple[PricingModelSpec, SuperGLM]:
        """Bind this recipe to a dataset and return its spec and unfitted estimator.

        Apply the spec's transforms to ``dataset.df`` before passing the prepared
        data to ``fit_model``. This method constructs objects without fitting them.
        """

        from pricing_pipeline.notebook import PricingModelSpec

        data = self.document.to_dict()
        model = decode_estimator(
            data.pop("estimator"),
            data.pop("features"),
            data["feature_order"],
            data.pop("interactions"),
        )
        data["features"] = data.pop("feature_order")
        data["transforms"] = decode_transforms(data["transforms"], data.pop("transform_order"))
        data["validation"] = decode_validation(data["validation"])
        data.pop("format_version")
        return PricingModelSpec(dataset=dataset, **data), model

    @property
    def canonical_json(self) -> str:
        return self.document.canonical_json

    @property
    def sha256(self) -> str:
        return self.document.sha256


__all__ = [
    "ModelRecipe",
    "RecipeCapture",
    "RecipeDocument",
    "RecipeError",
    "UnsupportedRecipeError",
]
