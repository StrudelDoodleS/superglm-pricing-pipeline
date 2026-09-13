"""Locate SQL and notebook resources shipped in the installed distribution.

Use these accessors instead of paths relative to the repository checkout.
``materialized_migration_dir`` provides a filesystem path for its context's
lifetime when a caller cannot use an importlib resource directly.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path

_ROOT_PACKAGE = "pricing_pipeline.resources"


def migration_root() -> Traversable:
    """Return the installed SQL Server migration resources."""

    return files(_ROOT_PACKAGE).joinpath("migrations")


def offline_sqlite_root() -> Traversable:
    """Return the installed SQLite schema and view resources."""

    return files(_ROOT_PACKAGE).joinpath("offline_sqlite")


def scaffold_root() -> Traversable:
    """Return the installed project configuration, agent and notebook resources."""

    return files(_ROOT_PACKAGE).joinpath("scaffold")


def scaffold_template() -> Traversable:
    """Return the default pricing_scaffold.toml resource."""

    return scaffold_root().joinpath("pricing_scaffold.toml")


def scaffold_notebook_root() -> Traversable:
    """Return the six installed notebook templates."""

    return scaffold_root().joinpath("notebooks")


@contextmanager
def materialized_migration_dir() -> Iterator[Path]:
    """Yield a filesystem migration directory valid until the context exits."""

    with as_file(migration_root()) as path:
        yield path
