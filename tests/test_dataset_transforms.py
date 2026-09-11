from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from pricing_pipeline.data.dataset import PricingDataset
from pricing_pipeline.data.transforms import (
    Clip,
    Log,
    Log1p,
    apply_transforms,
    normalize_transforms,
    transforms_from_metadata,
    transforms_metadata,
)


def frame():
    return pd.DataFrame(
        {"id": [1, 2], "as_of": ["2026-06-30"] * 2, "x": [1.0, 4.0]},
        index=pd.Index([8, 3], name="original"),
    )


def dataset(df=None, **changes):
    options = {"name": "claims", "source": "warehouse", "key": "id", "as_of": "as_of"}
    options.update(changes)
    return PricingDataset(frame() if df is None else df, **options)


def test_transforms_preserve_raw_frame_index_and_output_order():
    raw = frame()
    actual = apply_transforms(raw, {"ln": Log("x"), "capped": Clip("x", upper=2)})
    expected = raw.assign(ln=[0.0, np.log(4)], capped=[1.0, 2.0])
    pd.testing.assert_frame_equal(actual, expected)
    actual.loc[8, "x"] = 90
    pd.testing.assert_frame_equal(raw, frame())
    copied = apply_transforms(raw, {})
    copied.loc[8, "x"] = 99
    pd.testing.assert_frame_equal(raw, frame())


def test_transform_metadata_is_json_native_immutable_and_round_trips():
    declarations = {"ln": Log("x"), "ln1": Log1p("x"), "cap": Clip("x", 0, 3)}
    frozen = normalize_transforms(declarations)
    declarations.clear()
    metadata = json.loads(json.dumps(transforms_metadata(frozen)))
    assert metadata == {
        "ln": {"operation": "log", "source": "x"},
        "ln1": {"operation": "log1p", "source": "x"},
        "cap": {"operation": "clip", "source": "x", "lower": 0.0, "upper": 3.0},
    }
    assert frozen["ln"].expression == "log(x)"
    assert frozen["ln1"].expression == "log1p(x)"
    pd.testing.assert_frame_equal(
        apply_transforms(frame(), transforms_from_metadata(metadata)),
        frame().assign(ln=[0.0, np.log(4)], ln1=[np.log(2), np.log(5)], cap=[1.0, 3.0]),
    )
    with pytest.raises(TypeError):
        frozen["new"] = Log("x")
    with pytest.raises(FrozenInstanceError):
        frozen["ln"].source = "other"


@pytest.mark.parametrize("values", [[True, False], ["1", "2"], [1, np.nan], [1, np.inf]])
def test_transforms_reject_nonfinite_or_nonnumeric_sources(values):
    raw = frame().assign(x=values)
    with pytest.raises((TypeError, ValueError), match="numeric|finite"):
        apply_transforms(raw, {"cap": Clip("x", upper=2)})


@pytest.mark.parametrize("transform,values", [(Log("x"), [0, 1]), (Log1p("x"), [-1, 0])])
def test_log_domains_are_validated(transform, values):
    with pytest.raises(ValueError, match="greater than"):
        apply_transforms(frame().assign(x=values), {"result": transform})


@pytest.mark.parametrize(
    "declarations,match",
    [
        ({"x": Log("x")}, "already exists"),
        ({"y": Log("missing")}, "source"),
        ({"a": Log("x"), "b": Log("a")}, "source|depend"),
        ({"": Log("x")}, "name"),
        ({"y": lambda x: x}, "transform|Transform"),
    ],
)
def test_invalid_transform_declarations_rejected(declarations, match):
    with pytest.raises((TypeError, ValueError), match=match):
        apply_transforms(frame(), declarations)


def test_duplicate_columns_rejected_even_without_transforms():
    raw = pd.DataFrame([[1, 2]], columns=["x", "x"])
    with pytest.raises(ValueError, match="unique|duplicate"):
        apply_transforms(raw, {})


@pytest.mark.parametrize("kwargs", [{}, {"lower": 4, "upper": 3}, {"lower": np.inf}])
def test_clip_requires_valid_finite_bounds(kwargs):
    with pytest.raises(ValueError, match="bound|lower|finite"):
        Clip("x", **kwargs)


def test_unknown_metadata_operation_and_fields_are_rejected():
    with pytest.raises(ValueError, match="operation"):
        transforms_from_metadata({"y": {"operation": "eval", "source": "x"}})
    with pytest.raises(ValueError, match="fields"):
        transforms_from_metadata({"y": {"operation": "log", "source": "x", "code": "x"}})


def test_absent_transform_metadata_means_no_transforms():
    assert dict(transforms_from_metadata(None)) == {}
    assert dict(normalize_transforms(None)) == {}
    assert transforms_metadata(None) == {}
    pd.testing.assert_frame_equal(apply_transforms(frame(), None), frame())


def test_defensive_copies_isolate_nested_object_cells():
    raw = frame().assign(details=pd.Series([["a"], ["b"]], index=frame().index, dtype=object))
    snapshot = dataset(raw)
    raw.loc[8, "details"].append("changed")
    exposed = snapshot.df
    exposed.loc[3, "details"].append("changed")
    assert snapshot.df.loc[8, "details"] == ["a"]
    assert snapshot.df.loc[3, "details"] == ["b"]
    transformed = apply_transforms(raw, {})
    transformed.loc[3, "details"].append("changed")
    assert raw.loc[3, "details"] == ["b"]


@pytest.mark.parametrize("axis", ["index", "columns"])
@pytest.mark.parametrize("mutated", ["original", "exposed", "transformed"])
def test_defensive_copies_isolate_axis_arrays(axis, mutated):
    raw = frame()
    # An object column index exposes a writable NumPy array, as numeric row indexes do.
    raw.columns = pd.Index(raw.columns, dtype=object)
    expected = raw.copy(deep=True)
    expected.index = raw.index.copy(deep=True)
    expected.columns = raw.columns.copy(deep=True)
    snapshot = dataset(raw)
    exposed = snapshot.df
    transformed = apply_transforms(raw, {})
    frames = {"original": raw, "exposed": exposed, "transformed": transformed}
    getattr(frames[mutated], axis).values[0] = 77 if axis == "index" else "changed"
    pd.testing.assert_frame_equal(snapshot.df, expected)
    for name, unmutated in frames.items():
        if name != mutated:
            pd.testing.assert_frame_equal(unmutated, expected)


@pytest.mark.parametrize(
    "bounds, expected, dtype",
    [
        ({"upper": 2.5}, [1.0, 2.5], "Float64"),
        ({"lower": 2.5}, [2.5, 4.0], "Float64"),
        ({"upper": 2}, [1, 2], "Int64"),
        ({"upper": 4.5}, [1, 4], "Int64"),
    ],
)
def test_nullable_integer_clip_promotes_only_when_fractional_bound_changes_values(
    bounds, expected, dtype
):
    raw = frame().assign(x=pd.array([1, 4], dtype="Int64"))
    actual = apply_transforms(raw, {"clipped": Clip("x", **bounds)})
    pd.testing.assert_series_equal(
        actual["clipped"],
        pd.Series(expected, index=raw.index, dtype=dtype, name="clipped"),
    )
    pd.testing.assert_series_equal(actual["x"], raw["x"])


def test_dataset_copies_input_and_exposed_frames_and_normalizes_keys():
    raw = frame()
    snapshot = dataset(raw)
    raw.loc[8, "x"] = 9
    exposed = snapshot.df
    exposed.loc[3, "x"] = 9
    pd.testing.assert_frame_equal(snapshot.df, frame())
    assert snapshot.key == ("id",)
    assert dataset(key=["as_of", "id"]).key == ("as_of", "id")
    with pytest.raises((AttributeError, FrozenInstanceError)):
        snapshot.name = "other"


@pytest.mark.parametrize(
    "raw,kwargs,match",
    [
        (frame().iloc[:0], {}, "empty"),
        (frame().assign(id=[1, 1]), {}, "unique"),
        (frame().assign(id=[1, None]), {}, "null"),
        (frame(), {"key": "missing"}, "missing"),
        (frame(), {"key": ["id", "id"]}, "duplicate"),
        (frame(), {"key": {"id"}}, "ordered|sequence"),
        (frame(), {"as_of": "missing"}, "missing"),
        (frame().assign(as_of=["2026-01-01", "2026-01-02"]), {}, "one date"),
        (frame().assign(as_of=[None, "2026-01-01"]), {}, "null"),
        (frame().assign(as_of=["no date"] * 2), {}, "date"),
        (frame(), {"name": " "}, "name"),
    ],
)
def test_dataset_rejects_invalid_identity_or_provenance(raw, kwargs, match):
    with pytest.raises((TypeError, ValueError), match=match):
        dataset(raw, **kwargs)


def test_dataset_roundtrip_and_identical_save_leave_artifact_untouched(tmp_path):
    path = tmp_path / "dataset.joblib"
    snapshot = dataset()
    assert snapshot.save(path) == path.resolve()
    original_bytes = path.read_bytes()
    original_metadata = path.with_suffix(".joblib.json").read_bytes()
    assert dataset().save(path) == path.resolve()
    assert path.read_bytes() == original_bytes
    assert path.with_suffix(".joblib.json").read_bytes() == original_metadata
    loaded = PricingDataset.load(path)
    pd.testing.assert_frame_equal(loaded.df, frame())
    assert (loaded.name, loaded.source, loaded.key, loaded.as_of) == (
        "claims",
        "warehouse",
        ("id",),
        "as_of",
    )


def test_save_rejects_unsupported_nested_values_with_actionable_error_before_writing(tmp_path):
    from pricing_pipeline.data.dataset import PricingDatasetError

    raw = frame().assign(details=pd.Series([["a"], ["b"]], index=frame().index, dtype=object))
    snapshot = dataset(raw)
    path = tmp_path / "dataset.joblib"
    with pytest.raises(PricingDatasetError, match="unsupported.*scalar"):
        snapshot.save(path)
    assert not path.exists()
    assert not path.with_suffix(".joblib.json").exists()


@pytest.mark.parametrize("change", ["data", "source", "index", "key"])
def test_dataset_changed_data_or_provenance_requires_replace(tmp_path, change):
    path = tmp_path / "dataset.joblib"
    dataset().save(path)
    raw = frame()
    kwargs = {}
    if change == "data":
        raw.loc[8, "x"] = 7
    elif change == "index":
        raw.index = [0, 1]
    elif change == "key":
        kwargs["key"] = ["as_of", "id"]
    else:
        kwargs["source"] = "another warehouse"
    replacement = dataset(raw, **kwargs)
    with pytest.raises(FileExistsError, match="replace=True"):
        replacement.save(path)
    replacement.save(path, replace=True)
    loaded = PricingDataset.load(path)
    pd.testing.assert_frame_equal(loaded.df, raw)
    assert loaded.source == replacement.source
    assert loaded.key == replacement.key


def test_artifact_corruption_is_rejected_before_deserializing(tmp_path, monkeypatch):
    path = tmp_path / "dataset.joblib"
    dataset().save(path)
    corrupted = bytearray(path.read_bytes())
    corrupted[-1] ^= 1
    path.write_bytes(corrupted)

    def unexpected_load(*args, **kwargs):
        pytest.fail("corrupt bytes must not reach deserialization")

    monkeypatch.setattr("pricing_pipeline.data.dataset.joblib.load", unexpected_load)
    with pytest.raises(ValueError, match="SHA-256"):
        PricingDataset.load(path)


def test_sidecar_provenance_is_bound_to_envelope(tmp_path):
    path = tmp_path / "dataset.joblib"
    dataset().save(path)
    sidecar = path.with_suffix(".joblib.json")
    metadata = json.loads(sidecar.read_text())
    metadata["source"] = "invented source"
    sidecar.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="metadata|provenance"):
        PricingDataset.load(path)


@pytest.mark.parametrize("change", ["value", "raw", "index", "row", "column", "missing"])
def test_prepared_validation_rejects_unrecorded_mutations(change):
    snapshot = dataset()
    transforms = {"log_x": Log("x")}
    prepared = apply_transforms(snapshot.df, transforms)
    snapshot.validate_prepared(prepared, transforms)
    if change == "value":
        prepared.loc[8, "log_x"] += 1e-10
    elif change == "raw":
        prepared.loc[8, "x"] = 5
    elif change == "index":
        prepared.index = [0, 1]
    elif change == "row":
        prepared = prepared.iloc[::-1]
    elif change == "column":
        prepared = prepared[prepared.columns[::-1]]
    else:
        prepared = prepared.drop(columns="log_x")
    with pytest.raises(ValueError, match="prepared|transforms"):
        snapshot.validate_prepared(prepared, transforms)
