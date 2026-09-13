"""Hash ordered row keys so saved split positions can be checked against data.

A change in row order must change this identity even when the row set is equal.
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd


def compute_row_order_sha256(
    frame: pd.DataFrame,
    *,
    pk_column: str | None = None,
    pk_columns: tuple[str, ...] | None = None,
) -> str:
    if pk_columns is None:
        if pk_column is None:
            raise ValueError("pk_column or pk_columns is required")
        pk_columns = (pk_column,)

    digest = hashlib.sha256()
    for row in frame.loc[:, list(pk_columns)].itertuples(index=False, name=None):
        digest.update(json.dumps(row, default=str, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
