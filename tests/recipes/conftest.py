import numpy as np
import pandas as pd
import pytest
from superglm import Categorical, Numeric, OrderedCategorical, Spline, SuperGLM, collapse_levels

from pricing_pipeline import notebook as api
from pricing_pipeline.models.config import ValidationSplitConfig


@pytest.fixture
def recipe_data():
    return dict(
        name="CLAIM_FREQUENCY",
        label="Claim frequency",
        model_type="frequency",
        deployment_slot="PRODUCTION",
        target="claim_count",
        features={
            "region": {
                "type": "Categorical",
                "base": "A",
                "groups": [{"name": "A", "levels": ["A"]}, {"name": "BC", "levels": ["B", "C"]}],
            },
            "x": {"type": "Numeric"},
        },
        estimator={"family": "poisson", "retain_fit_state": False},
    )


@pytest.fixture
def grouped_model_case():
    rng = np.random.default_rng(83)
    n = 420
    df = pd.DataFrame(
        {
            "id": np.arange(n),
            "as_of": ["2026-09-01"] * n,
            "region": np.resize(["A", "B", "C"], n),
            "bonus_malus": np.resize(["0", "1", "2", "3", "4", "Unknown"], n),
            "x": rng.uniform(0, 5, n),
            "z": rng.normal(size=n),
            "exposure": rng.uniform(0.5, 1.5, n),
        }
    )
    df["claim_count"] = rng.poisson(df.exposure * np.exp(0.7 + 0.1 * df.x))
    dataset = api.PricingDataset(df, name="claims", source="test", key="id", as_of="as_of")
    features = {
        "region": Categorical(
            base="A", grouping=collapse_levels(df.region, groups={"BC": ["B", "C"]})
        ),
        "bonus_malus": OrderedCategorical(
            order=["0", "1", "2", "3", "4"],
            specials=["Unknown"],
            base="0",
            basis=Spline("cr", k=3, knot_strategy="quantile"),
        ),
        "x": Spline("cr", k=3, knot_strategy="quantile"),
        "z": Numeric(),
    }
    spec = api.PricingModelSpec(
        name="CLAIM_FREQUENCY",
        label="Claim frequency",
        model_type="frequency",
        deployment_slot="PRODUCTION",
        target="claim_count",
        dataset=dataset,
        features=tuple(features),
        transforms={"log_exposure": api.Log("exposure")},
        offset_column="log_exposure",
        export_weight_column="exposure",
        validation=ValidationSplitConfig.kfold(n_splits=3),
    )
    return dataset, spec, SuperGLM(features=features, selection_penalty=0.0, retain_fit_state=False)
