"""Notebook splitters preserve exact memberships and their SQL provenance."""

import json
from dataclasses import replace

import joblib
import numpy as np
import pytest
from sklearn.model_selection import GroupKFold, KFold, TimeSeriesSplit
from sqlalchemy import text
from superglm import Categorical, Numeric, SuperGLM

from pricing_pipeline import notebook as api
from pricing_pipeline.models.config import ValidationSplitConfig
from tests.test_notebook_dataset_spec import _dataset, _spec


class CalendarSplit:
    def __init__(self, training_rows=45):
        self.training_rows = training_rows
        self.calls = 0

    def split(self, X, y=None, groups=None):
        self.calls += 1
        assert "event_date" in X
        assert y.name == "y"
        yield np.arange(self.training_rows), np.arange(self.training_rows, len(X))


@pytest.mark.parametrize("kind", ["group", "time", "custom"])
def test_splitter_build_saves_exact_folds_and_metadata(tmp_path, kind):
    dataset = _dataset()
    raw = dataset.df
    raw["customer_id"] = np.repeat(np.arange(30), 3)
    raw["event_date"] = np.repeat(np.arange(15), 6)
    dataset = api.PricingDataset(
        raw, name=dataset.name, source=dataset.source, key=dataset.key, as_of=dataset.as_of
    )
    splitter = {
        "group": GroupKFold(n_splits=3),
        "time": TimeSeriesSplit(n_splits=3, test_size=15, gap=3, max_train_size=30),
        "custom": CalendarSplit(),
    }[kind]
    kwargs = {"groups_column": "customer_id"} if kind == "group" else {}
    spec = _spec(dataset, validation=splitter, fit_mode="fit_reml", **kwargs)
    # Replacing unrelated spec fields must retain the splitter.
    spec = replace(spec, scoring=("deviance",))
    df = api.apply_transforms(dataset.df, spec.transforms)
    original = df.copy()
    source_root = tmp_path / "model"
    source_root.mkdir()
    (source_root / "model.py").write_text("# Splitter integration test\n")
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    try:
        registered = api.register_model(pricing, spec, source_root=source_root)
        candidate = api.fit_model(
            pricing,
            model=registered,
            frame=df,
            superglm_model=SuperGLM(
                family="poisson",
                selection_penalty=0.0,
                retain_fit_state=False,
                features={"log_x": Numeric(), "segment": Categorical()},
            ),
        )
        saved = api.save_model_version(pricing, candidate)
        bundle = joblib.load(candidate.completed_build.candidate_artifact_path)["bundle"]
        with pricing.engine.connect() as c:
            split = c.execute(text("SELECT * FROM pricing.CV_SPLIT_SET")).mappings().one()
            assert c.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RUN")).scalar_one() == 1
            fold_count = c.execute(text("SELECT COUNT(*) FROM pricing.CV_FOLD")).scalar_one()
        assert split["splitter_class"].endswith(type(splitter).__name__)
        assert split["split_mode"] == "MATERIALIZED"
        params = json.loads(split["splitter_params_json"])
        with np.load(split["artifact_uri"], allow_pickle=False) as artifact:
            assert artifact["split_format"].item() == "explicit_indices_v1"
            pairs = [
                (artifact[f"fold_{i}_train_idx"], artifact[f"fold_{i}_test_idx"])
                for i in range(1, fold_count + 1)
            ]
        if kind == "group":
            assert split["groups_column"] == "customer_id"
            assert params["n_splits"] == 3
            assert fold_count == 3
            for train, test in pairs:
                assert set(df.customer_id.iloc[train]).isdisjoint(df.customer_id.iloc[test])
            assert candidate.metrics["cv_oof_coverage"] == 1.0
        elif kind == "time":
            assert params["gap"] == 3 and params["max_train_size"] == 30
            for i, (train, test) in enumerate(pairs):
                np.testing.assert_array_equal(train, np.arange(12 + 15 * i, 42 + 15 * i))
                np.testing.assert_array_equal(test, np.arange(45 + 15 * i, 60 + 15 * i))
            assert candidate.metrics["cv_oof_coverage"] == 0.5
        else:
            assert splitter.calls == 1
            assert params["training_rows"] == 45
            np.testing.assert_array_equal(pairs[0][0], np.arange(45))
            np.testing.assert_array_equal(pairs[0][1], np.arange(45, 90))
        # Recorded split membership must be the membership that produced OOF scores.
        for (train, test), recorded in zip(pairs, bundle.cv_report["fold_indices"], strict=True):
            np.testing.assert_array_equal(train, recorded["train"])
            np.testing.assert_array_equal(test, recorded["test"])
        assert saved.rate_package_id == 1
        assert df.equals(original)
    finally:
        pricing.engine.dispose()


def test_splitter_metadata_rejects_nonserializable_settings():
    with pytest.raises(ValueError, match="splitter.*parameter|splitter.*JSON"):
        _spec(_dataset(), validation=KFold(shuffle=True, random_state=np.random.RandomState(42)))


def test_groups_column_requires_splitter():
    with pytest.raises(ValueError, match="groups_column.*splitter"):
        _spec(_dataset(), validation=ValidationSplitConfig.kfold(), groups_column="customer")


@pytest.mark.parametrize("groups_column", ["missing", "segment"])
def test_missing_or_null_groups_rejected_before_fit(tmp_path, groups_column):
    dataset = _dataset()
    if groups_column == "segment":
        raw = dataset.df
        raw.loc[0, "segment"] = None
        dataset = api.PricingDataset(
            raw, name=dataset.name, source=dataset.source, key=dataset.key, as_of=dataset.as_of
        )
    spec = _spec(dataset, validation=GroupKFold(3), groups_column=groups_column)
    df = api.apply_transforms(dataset.df, spec.transforms)
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    try:
        model = api.register_model(pricing, spec, source_root=tmp_path)
        with pytest.raises(ValueError, match="missing|group.*null"):
            api.fit_model(pricing, model=model, frame=df, superglm_model=object())
    finally:
        pricing.engine.dispose()


class RepeatedTestSplit(CalendarSplit):
    def split(self, X, y=None, groups=None):
        yield np.arange(45), np.arange(45, 90)
        yield np.arange(45), np.arange(45, 90)


def test_splitter_rejects_repeated_test_rows_before_training(tmp_path):
    dataset = _dataset()
    spec = _spec(dataset, validation=RepeatedTestSplit())
    df = api.apply_transforms(dataset.df, spec.transforms)
    pricing = api.connect(mode="local", local_root=tmp_path / "local")
    try:
        model = api.register_model(pricing, spec, source_root=tmp_path)
        with pytest.raises(ValueError, match="duplicate test-row membership"):
            api.fit_model(pricing, model=model, frame=df, superglm_model=object())
        with pricing.engine.connect() as c:
            assert c.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RUN")).scalar_one() == 0
            assert (
                c.execute(
                    text("SELECT COUNT(*) FROM pricing.PRICING_MODEL_VERSION_RESERVATION")
                ).scalar_one()
                == 0
            )
    finally:
        pricing.engine.dispose()


def test_splitter_settings_are_snapshotted_and_part_of_split_identity():
    from pricing_pipeline.data.manifest import split_set_id_for_validation_split
    from pricing_pipeline.data.validation import splitter_config

    splitter = CalendarSplit(training_rows=45)
    config = splitter_config(splitter, groups_column=None)
    splitter.training_rows = 60
    assert config.splitter_params == {"training_rows": 45}
    kwargs = {
        "manifest_id": "same-data",
        "row_order_sha256": "a" * 64,
        "split_indices": [(np.arange(45), np.arange(45, 90))],
    }
    original = split_set_id_for_validation_split(validation_split=config, **kwargs)
    for changed in (
        replace(config, splitter_class="another.CalendarSplit"),
        replace(config, splitter_params={"training_rows": 60}),
        replace(config, groups_column="customer_id"),
    ):
        assert split_set_id_for_validation_split(validation_split=changed, **kwargs) != original
