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
    document: RecipeDocument

    @classmethod
    def from_model(cls, model: SuperGLM, *, spec: PricingModelSpec) -> ModelRecipe:
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
        return cls(io.load(path))

    def save(self, path: str | Path, *, replace: bool = False) -> Path:
        return io.save(self.document, path, replace=replace)

    def build(self, *, dataset: PricingDataset) -> tuple[PricingModelSpec, SuperGLM]:
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
