import pytest

from pricing_pipeline.modeling.recipes.schema import RecipeCapture, RecipeDocument, RecipeError


def test_snapshot_is_deeply_immutable(recipe_data):
    doc = RecipeDocument(**recipe_data)
    recipe_data["features"]["region"]["base"] = "B"
    assert doc.features["region"]["base"] == "A"
    with pytest.raises(TypeError):
        doc.features["region"]["groups"][0]["levels"][0] = "B"
    with pytest.raises(TypeError):
        doc.estimator["family"] = "gamma"


@pytest.mark.parametrize(
    "change",
    [
        {"format_version": 2},
        {"features": True},
        {"transforms": 5},
        {"recipe_revision": 1},
        {"estimator": {"tol": float("nan")}},
        {"estimator": {"tol": float("inf")}},
    ],
)
def test_bad_document_fails(recipe_data, change):
    with pytest.raises(RecipeError):
        RecipeDocument(**(recipe_data | change))


def test_capture_roundtrip_and_tamper(recipe_data):
    doc = RecipeDocument(**recipe_data)
    capture = RecipeCapture.captured(doc)
    assert RecipeCapture.from_payload(capture.to_payload()) == capture
    payload = capture.to_payload()
    payload["document"]["features"]["region"]["base"] = "B"
    with pytest.raises(RecipeError, match="checksum|canonical"):
        RecipeCapture.from_payload(payload)


@pytest.mark.parametrize(
    "feature",
    [
        True,
        {
            "type": "Categorical",
            "groups": [{"name": "AB", "levels": ["A", "B"]}, {"name": "B", "levels": ["B"]}],
        },
        {
            "type": "OrderedCategorical",
            "order": ["0", "1", "2", "3"],
            "specials": ["Unknown"],
            "groups": [{"name": "bad", "levels": ["Unknown", "0"]}],
        },
        {"type": "OrderedCategorical", "order": [1, "1", 2]},
    ],
)
def test_malformed_features_fail_with_path(recipe_data, feature):
    recipe_data["features"]["region"] = feature
    with pytest.raises(RecipeError, match="features.region"):
        RecipeDocument(**recipe_data)


def test_omitted_constructor_defaults_match_explicit(recipe_data):
    implicit = RecipeDocument(**recipe_data)
    assert RecipeDocument(**implicit.to_dict()).sha256 == implicit.sha256


@pytest.mark.parametrize(
    "change, path",
    [
        ({"format_version": True}, "format_version"),
        ({"scoring": "deviance"}, "scoring"),
        ({"scoring": []}, "scoring"),
        ({"scoring": ["deviance", "deviance"]}, "scoring"),
        ({"offset_column": "log_exposure"}, "offset"),
        ({"groups_column": "group"}, "groups_column"),
        ({"sample_weight_column": "region"}, "roles"),
        ({"transforms": {"log_exposure": True}}, "transforms.log_exposure"),
        ({"estimator": {"family": True}}, "estimator.family"),
    ],
)
def test_invalid_declared_controls_fail_at_load(recipe_data, change, path):
    with pytest.raises(RecipeError, match=path):
        RecipeDocument(**(recipe_data | change))


def test_transform_offset_defaults_are_normalized_before_hashing(recipe_data):
    data = recipe_data | {
        "transforms": {"log_exposure": {"type": "Log", "source": "exposure"}},
        "offset_column": "log_exposure",
    }
    implicit = RecipeDocument(**data)
    explicit = RecipeDocument(
        **(data | {"offset_source_column": "exposure", "offset_label": "log(exposure)"})
    )
    assert implicit.sha256 == explicit.sha256
    assert implicit.offset_source_column == "exposure"
    with pytest.raises(RecipeError, match="offset_label"):
        RecipeDocument(**(data | {"offset_label": "different"}))


def test_build_evidence_imports_without_prior_notebook_import(tmp_path):
    import subprocess
    import sys

    subprocess.run(
        [
            sys.executable,
            "-c",
            "from pricing_pipeline.models.spec import ApprovedModelBuild; from pricing_pipeline.modeling import ModelInputs",
        ],
        cwd=tmp_path,
        check=True,
    )
