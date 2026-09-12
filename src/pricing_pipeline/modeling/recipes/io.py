"""Safe TOML editing files. Reading never executes Python or opens a database."""

from __future__ import annotations

import os
import tempfile
import tomllib
from pathlib import Path

import tomli_w

from .schema import RecipeDocument, RecipeError

COMMENTS = """# Declared model choices for refitting. SQL assigns revisions when a build is saved.
# Groups list every declared member, including singleton groups. Specials are free
# levels outside an ordered smooth and cannot be merged into a group.
# Constructor defaults are explicit. { none = true } records an unset option.
# Loading refits declared choices; learned knots, bases and coefficients are absent.
"""


def _nullable(path):
    """Null markers apply only to known optional constructor/spec fields."""
    if len(path) == 1:
        return path[0] in {
            "groups_column",
            "offset_column",
            "offset_source_column",
            "offset_label",
            "sample_weight_column",
            "export_weight_column",
        }
    if path[0] == "estimator":
        return (
            len(path) == 2
            and path[1]
            in {"link", "penalty", "selection_penalty", "spline_penalty", "penalty_features"}
        ) or (
            len(path) > 2 and path[1] == "penalty" and path[-1] in {"lambda1", "flavor", "features"}
        )
    if path[0] == "features" and len(path) >= 3:
        return path[-1] in {
            "group_domain",
            "levels",
            "knots",
            "boundary",
            "discrete",
            "n_bins",
            "constraint",
            "lambda_policy",
            "value",
        }
    if path[0] == "transforms" and len(path) == 3:
        return path[-1] in {"lower", "upper"}
    if path[0] == "validation" and len(path) == 2:
        return path[-1] in {
            "n_splits",
            "test_size",
            "random_state",
            "stratify_column",
            "column",
            "max_train_size",
        }
    return False


def _nulls(value, *, encode, path=()):
    if encode and value is None:
        return {"none": True}
    if (
        not encode
        and isinstance(value, dict)
        and set(value) == {"none"}
        and value["none"] is True
        and _nullable(path)
    ):
        return None
    if isinstance(value, dict):
        return {key: _nulls(item, encode=encode, path=(*path, key)) for key, item in value.items()}
    if isinstance(value, list):
        return [
            _nulls(item, encode=encode, path=(*path, index)) for index, item in enumerate(value)
        ]
    return value


def _path(path):
    target = Path(path).expanduser().absolute()
    if any(part == ".." for part in target.parts):
        raise RecipeError("recipe path: parent traversal is not allowed")
    if any(part.is_symlink() for part in (target, *target.parents)):
        raise RecipeError("recipe path: symlinks are not allowed")
    if target.suffix.lower() != ".toml":
        raise RecipeError("recipe path: expected a .toml file")
    return target


def load(path):
    target = _path(path)
    try:
        with target.open("rb") as stream:
            data = tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        raise RecipeError(f"recipe TOML: {exc}") from exc
    return RecipeDocument(**_nulls(data, encode=False))


def save(document, path, *, replace=False):
    target = _path(path)
    if target.exists() and not replace:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = COMMENTS + tomli_w.dumps(_nulls(document.to_dict(), encode=True))
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        _path(target)
        if replace:
            os.replace(temporary, target)
        else:
            # Atomic no-clobber publication. A concurrent writer cannot be overwritten.
            os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
