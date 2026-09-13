"""Define model registration, validation and completed-build records.

``pricing`` owns the analyst-facing PricingModelSpec; ``config`` describes
registration and splits, ``kinds`` names build origins, and ``spec`` validates
the evidence passed to publication. Estimator fitting
lives in the separate ``modeling`` package.
"""
