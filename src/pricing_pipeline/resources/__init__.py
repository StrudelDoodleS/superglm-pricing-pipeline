from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path

_ROOT_PACKAGE = "pricing_pipeline.resources"


def migration_root() -> Traversable:
    return files(_ROOT_PACKAGE).joinpath("migrations")


def offline_sqlite_root() -> Traversable:
    return files(_ROOT_PACKAGE).joinpath("offline_sqlite")


def scaffold_root() -> Traversable:
    return files(_ROOT_PACKAGE).joinpath("scaffold")


@contextmanager
def materialized_migration_dir() -> Iterator[Path]:
    with as_file(migration_root()) as path:
        yield path
