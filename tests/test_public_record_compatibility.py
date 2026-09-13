"""Saved records must still resolve their original public Python class paths."""

import pickle

import pytest


@pytest.mark.parametrize(
    ("module", "name", "args", "attribute", "expected"),
    [
        (
            "pricing_pipeline.modeling.monitoring",
            "ModelFitContract",
            ('{"terms":[]}', "a" * 64, "b" * 64, "0.30.0"),
            "contract_json",
            '{"terms":[]}',
        ),
        (
            "pricing_pipeline.reporting.evidence",
            "EvidenceFact",
            ("fit", "REML"),
            "value",
            "REML",
        ),
    ],
)
def test_saved_public_record_path_still_deserializes(module, name, args, attribute, expected):
    # Protocol 0 GLOBAL/REDUCE describes records saved at the original import path.
    # It does not use the relocated class's __module__ to construct the fixture.
    arguments = pickle.dumps(args, protocol=0)
    fixture = f"c{module}\n{name}\n".encode() + arguments[:-1] + b"R."
    record = pickle.loads(fixture)
    assert getattr(record, attribute) == expected
    assert pickle.loads(pickle.dumps(record)) == record


def test_pricing_spec_remains_constructible_through_original_notebook_path():
    from pricing_pipeline.notebook import PricingModelSpec

    stored_class = pickle.loads(b"cpricing_pipeline.notebook\nPricingModelSpec\n.")
    spec = stored_class(
        name="FREQUENCY",
        label="Frequency",
        target="claims",
        model_type="poisson",
        deployment_slot="UAT",
        features=("age",),
        dataset_name="policies",
        source_system="test",
        pk_columns=("id",),
    )
    assert isinstance(spec, PricingModelSpec)
    assert spec.features == ("age",)
