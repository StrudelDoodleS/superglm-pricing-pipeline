"""A named dataset snapshot with verified local persistence and provenance."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from pricing_pipeline.data.frame_artifact import _write_json_atomic
from pricing_pipeline.data.manifest import _normalise_date, model_frame_evidence
from pricing_pipeline.data.transforms import Transform, _copy_frame, apply_transforms

_FORMAT = "pricing-dataset-joblib-v1"


class PricingDatasetError(ValueError):
    """A persisted dataset is incomplete or fails its integrity checks."""


def _text(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, init=False, eq=False)
class PricingDataset:
    """Keep a defensive frame snapshot and the provenance needed to identify it."""

    _df: pd.DataFrame = field(repr=False)
    name: str
    source: str
    key: tuple[str, ...]
    as_of: str

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        name: str,
        source: str,
        key: str | Sequence[str],
        as_of: str,
    ) -> None:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("df must be a pandas DataFrame")
        if df.empty:
            raise ValueError("dataset must not be empty")
        if not df.columns.is_unique:
            raise ValueError("dataset column names must be unique")
        if any(not isinstance(column, str) or not column.strip() for column in df.columns):
            raise ValueError("dataset column names must be non-empty strings")
        if isinstance(key, str):
            keys = (key,)
        elif isinstance(key, Sequence):
            keys = tuple(key)
        else:
            raise TypeError("key must be a column name or ordered sequence of column names")
        if not keys:
            raise ValueError("key must contain at least one column")
        keys = tuple(_text(column, field="key") for column in keys)
        if len(set(keys)) != len(keys):
            raise ValueError("key must not contain duplicate columns")
        as_of = _text(as_of, field="as_of")
        missing = [column for column in (*keys, as_of) if column not in df.columns]
        if missing:
            raise ValueError(f"dataset is missing required columns: {missing}")
        if df[list(keys)].isna().any().any():
            raise ValueError("dataset key columns must not contain null values")
        if df.duplicated(subset=list(keys)).any():
            raise ValueError("dataset key must uniquely identify each row")
        if df[as_of].isna().any():
            raise ValueError("dataset as_of column must not contain null values")
        dates = {_normalise_date(value, field_name="as_of") for value in df[as_of]}
        if len(dates) != 1:
            raise ValueError("dataset as_of column must contain exactly one date")
        object.__setattr__(self, "_df", _copy_frame(df))
        object.__setattr__(self, "name", _text(name, field="name"))
        object.__setattr__(self, "source", _text(source, field="source"))
        object.__setattr__(self, "key", keys)
        object.__setattr__(self, "as_of", as_of)

    @property
    def df(self) -> pd.DataFrame:
        return _copy_frame(self._df)

    def _metadata(self) -> dict[str, Any]:
        try:
            frame_sha256 = model_frame_evidence(self._df)[0]
        except (TypeError, ValueError) as exc:
            raise PricingDatasetError(
                "dataset contains unsupported data for frame evidence; "
                "convert nested or unhashable values to scalar columns before saving"
            ) from exc
        return {
            "format": _FORMAT,
            "name": self.name,
            "source": self.source,
            "key": list(self.key),
            "as_of": self.as_of,
            "model_frame_sha256": frame_sha256,
        }

    def validate_prepared(
        self, df: pd.DataFrame, transforms: Mapping[str, Transform] | None
    ) -> None:
        """Reject any prepared frame that differs from the declared computation."""
        expected = apply_transforms(self._df, transforms)
        try:
            pd.testing.assert_frame_equal(
                df,
                expected,
                check_exact=True,
                check_index_type=True,
                check_column_type=True,
            )
        except (AssertionError, TypeError) as exc:
            raise ValueError(
                "prepared dataframe differs from the dataset and declared transforms"
            ) from exc

    def save(self, path: str | Path, *, replace: bool = False) -> Path:
        """Persist a trusted local joblib envelope and JSON integrity receipt.

        Values must support the pipeline's scalar frame evidence. Unsupported
        nested values raise PricingDatasetError before any files are written.
        """
        path = Path(path).expanduser().resolve()
        sidecar = path.with_suffix(f"{path.suffix}.json")
        metadata = self._metadata()
        if path.exists() or sidecar.exists():
            try:
                previous = self.load(path)
            except PricingDatasetError:
                if not replace:
                    raise
            else:
                try:
                    pd.testing.assert_frame_equal(
                        previous._df,
                        self._df,
                        check_exact=True,
                        check_index_type=True,
                        check_column_type=True,
                    )
                except AssertionError:
                    equal = False
                else:
                    equal = previous._metadata() == metadata
                if equal:
                    return path
                if not replace:
                    raise FileExistsError(
                        f"a different dataset or provenance already exists; set replace=True: {path}"
                    )
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            joblib.dump({"metadata": metadata, "frame": self._df}, temporary, compress=3)
            artifact_bytes = temporary.read_bytes()
            receipt = {
                **metadata,
                "size_bytes": len(artifact_bytes),
                "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
            }
            os.replace(temporary, path)
            _write_json_atomic(receipt, sidecar)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    @classmethod
    def load(cls, path: str | Path) -> PricingDataset:
        """Check receipt bytes before deserializing a trusted local dataset file."""
        path = Path(path).expanduser().resolve()
        sidecar = path.with_suffix(f"{path.suffix}.json")
        try:
            receipt = json.loads(sidecar.read_text(encoding="utf-8"))
            artifact_bytes = path.read_bytes()
        except (OSError, ValueError) as exc:
            raise PricingDatasetError("dataset artifact or metadata could not be read") from exc
        if not isinstance(receipt, dict) or receipt.get("format") != _FORMAT:
            raise PricingDatasetError("invalid dataset metadata format")
        if len(artifact_bytes) != receipt.get("size_bytes"):
            raise PricingDatasetError("dataset artifact size does not match its metadata")
        if hashlib.sha256(artifact_bytes).hexdigest() != receipt.get("sha256"):
            raise PricingDatasetError("dataset artifact SHA-256 does not match its metadata")
        try:
            envelope = joblib.load(io.BytesIO(artifact_bytes))
        except Exception as exc:
            raise PricingDatasetError("dataset artifact could not be deserialized") from exc
        metadata = {
            key: value for key, value in receipt.items() if key not in {"size_bytes", "sha256"}
        }
        if not isinstance(envelope, dict) or envelope.get("metadata") != metadata:
            raise PricingDatasetError("dataset envelope metadata does not match receipt provenance")
        try:
            snapshot = cls(
                envelope["frame"],
                name=metadata["name"],
                source=metadata["source"],
                key=metadata["key"],
                as_of=metadata["as_of"],
            )
            if snapshot._metadata() != metadata:
                raise PricingDatasetError("loaded dataset evidence does not match its metadata")
        except (KeyError, TypeError, ValueError) as exc:
            raise PricingDatasetError("dataset envelope or metadata is invalid") from exc
        return snapshot


__all__ = ["PricingDataset", "PricingDatasetError"]
