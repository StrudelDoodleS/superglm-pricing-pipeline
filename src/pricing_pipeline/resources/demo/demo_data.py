"""Synthetic source rows for the local SQL Server demonstration."""

import numpy as np
import pandas as pd


def synthetic_burn_cost(
    *, rows: int, seed: int, as_of: str, monitoring: bool = False
) -> pd.DataFrame:
    """Draw compound Poisson-gamma losses with Tweedie power 1.5.

    The target is loss per exposure. Exposure is the fitting weight. The later
    snapshot has modest claims inflation and a larger North region share.
    """
    rng = np.random.default_rng(seed)
    regions = ["North", "South", "East", "West"]
    region = rng.choice(regions, rows, p=[0.40, 0.20, 0.20, 0.20] if monitoring else [0.25] * 4)
    bonus = np.resize(np.array(["0", "1", "2", "3", "4", "Unknown"]), rows)
    rng.shuffle(bonus)
    age = rng.uniform(20 if monitoring else 18, 78 if monitoring else 80, rows)
    exposure = rng.uniform(0.5, 1.5, rows)
    ordered_effect = (
        pd.Series(bonus)
        .map({"0": 0.0, "1": 0.04, "2": 0.12, "3": 0.25, "4": 0.40, "Unknown": 0.18})
        .to_numpy()
    )
    mean_cost = np.exp(5.5 + 0.24 * (region == "North") + ordered_effect + 0.0005 * (age - 45) ** 2)
    mean_cost *= 1.12 if monitoring else 1.0
    dispersion = 35.0
    claim_count = rng.poisson(exposure * np.sqrt(mean_cost) / (0.5 * dispersion))
    total_loss = np.zeros(rows)
    positive = claim_count > 0
    total_loss[positive] = rng.gamma(
        claim_count[positive], 0.5 * dispersion * np.sqrt(mean_cost[positive])
    )
    return pd.DataFrame(
        {
            "policy_id": np.arange(rows) + (10_000 if monitoring else 0),
            "as_of": as_of,
            "region": region,
            "bonus_malus": bonus,
            "driver_age": age,
            "exposure": exposure,
            "burn_cost": total_loss / exposure,
        }
    )
