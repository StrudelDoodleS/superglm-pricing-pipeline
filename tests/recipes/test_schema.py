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
