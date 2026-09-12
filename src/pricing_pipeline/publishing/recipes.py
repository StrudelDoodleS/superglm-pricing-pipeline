"""Allocate immutable per-model recipe revisions in the publication transaction."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.recipes import ModelRecipe
from pricing_pipeline.modeling.recipes.schema import RecipeError


@dataclass(frozen=True)
class StoredRecipe:
    recipe_id: int
    recipe_revision: int
    recipe_sha256: str


def lock_model(connection, model_id):
    """Serialize all publication decisions for a model, including legacy builds."""
    schema = schema_names_from_connectable(connection).pricing
    if connection.dialect.name == "sqlite":
        # sqlite3's deferred transaction mode does not BEGIN for SELECT. Establish
        # the write transaction before reading MAX/retry identity; never commit it.
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        lock = ""
    else:
        lock = " WITH (UPDLOCK, HOLDLOCK)"
    exists = connection.execute(
        text(f"SELECT model_id FROM {schema}.PRICING_MODEL{lock} WHERE model_id=:model_id"),
        {"model_id": model_id},
    ).scalar_one_or_none()
    if exists is None:
        raise RecipeError(f"model_id: registered model {model_id} does not exist")


def resolve_recipe(
    connection, *, model_id: int, recipe: ModelRecipe, created_by: str
) -> StoredRecipe:
    lock_model(connection, model_id)
    schema = schema_names_from_connectable(connection).pricing
    params = {"model_id": model_id, "sha256": recipe.sha256}
    row = (
        connection.execute(
            text(
                f"SELECT recipe_id, recipe_revision, recipe_sha256, recipe_json, recipe_format_version FROM {schema}.MODEL_RECIPE WHERE model_id=:model_id AND recipe_sha256=:sha256"
            ),
            params,
        )
        .mappings()
        .one_or_none()
    )
    if row is not None:
        if (
            row["recipe_json"] != recipe.canonical_json
            or row["recipe_format_version"] != recipe.document.format_version
        ):
            raise RecipeError(
                "stored recipe checksum matches different canonical content; recipe integrity failure"
            )
        return StoredRecipe(
            int(row["recipe_id"]), int(row["recipe_revision"]), row["recipe_sha256"]
        )
    revision = connection.execute(
        text(
            f"SELECT COALESCE(MAX(recipe_revision), 0) + 1 FROM {schema}.MODEL_RECIPE WHERE model_id=:model_id"
        ),
        params,
    ).scalar_one()
    connection.execute(
        text(
            f"INSERT INTO {schema}.MODEL_RECIPE (model_id, recipe_revision, recipe_sha256, recipe_format_version, recipe_json, created_by) VALUES (:model_id, :revision, :sha256, :format, :json, :created_by)"
        ),
        params
        | {
            "revision": revision,
            "format": recipe.document.format_version,
            "json": recipe.canonical_json,
            "created_by": created_by,
        },
    )
    recipe_id = connection.execute(
        text(
            f"SELECT recipe_id FROM {schema}.MODEL_RECIPE WHERE model_id=:model_id AND recipe_sha256=:sha256"
        ),
        params,
    ).scalar_one()
    return StoredRecipe(int(recipe_id), int(revision), recipe.sha256)


def run_recipe_params(connection, build):
    capture = build.recipe_capture
    stored = (
        None
        if capture.status != "CAPTURED"
        else resolve_recipe(
            connection,
            model_id=build.model_id,
            recipe=ModelRecipe(capture.document),
            created_by=build.created_by,
        )
    )
    return {
        "recipe_id": None if stored is None else stored.recipe_id,
        "recipe_status": capture.status,
        "recipe_unavailable_reason": capture.unavailable_reason,
    }


def recipe_result(connection, model_run_id):
    schema = schema_names_from_connectable(connection).pricing
    row = (
        connection.execute(
            text(
                f"SELECT mr.recipe_status, r.recipe_revision, r.recipe_sha256 FROM {schema}.MODEL_RUN AS mr LEFT JOIN {schema}.MODEL_RECIPE AS r ON r.model_id=mr.model_id AND r.recipe_id=mr.recipe_id WHERE mr.model_run_id=:run"
            ),
            {"run": model_run_id},
        )
        .mappings()
        .one()
    )
    return dict(row)


def identity_params(build):
    return {
        "recipe_status": build.recipe_status,
        "recipe_sha256": build.recipe_sha256,
        "recipe_split_set_id": build.split_set_id,
    }


def identity_predicate(*, split="split_link.split_set_id"):
    """The same predicate is used before staging and inside both write paths."""
    return f"""AND mr.recipe_status IN ('CAPTURED', 'LEGACY')
    AND mr.recipe_status = :recipe_status
    AND (recipe.recipe_sha256 = :recipe_sha256 OR (recipe.recipe_sha256 IS NULL AND :recipe_sha256 IS NULL))
    AND ({split} = :recipe_split_set_id OR ({split} IS NULL AND :recipe_split_set_id IS NULL))"""
