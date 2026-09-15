"""Allocate and verify recipe revisions within a publication transaction.

Lock the registered model, reuse an identical canonical recipe or allocate
its next revision. Compare stored content as well as its hash on reuse.
TOML editing and estimator reconstruction belong to ``modeling.recipes``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import text

from pricing_pipeline.infra.schema import schema_names_from_connectable
from pricing_pipeline.modeling.recipes import ModelRecipe, RecipeCapture, RecipeDocument
from pricing_pipeline.modeling.recipes.schema import RecipeError


@dataclass(frozen=True)
class StoredRecipe:
    """The SQL identity, revision and hash of a registered model recipe."""

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


def validate_recipe_content(row, *, recipe: ModelRecipe):
    """A matching digest is insufficient: require the exact canonical document."""
    if (
        row.get("recipe_sha256") != recipe.sha256
        or row.get("recipe_json") != recipe.canonical_json
        or row.get("recipe_format_version") != recipe.document.format_version
    ):
        raise RecipeError(
            "stored recipe checksum matches different canonical content or format; recipe integrity failure"
        )


def validate_recipe_capture(row, capture):
    """Validate a SQL recipe match against independently verified build evidence."""
    if row.get("recipe_status", "LEGACY") != capture.status:
        raise RecipeError(
            "stored recipe status disagrees with captured evidence; recipe integrity failure"
        )
    if capture.status == "CAPTURED":
        validate_recipe_content(row, recipe=ModelRecipe(capture.document))


def _run_recipe(connection, model_run_id):
    schema = schema_names_from_connectable(connection).pricing
    row = (
        connection.execute(
            text(f"""SELECT run.recipe_status, run.recipe_unavailable_reason,
                       recipe.recipe_json, recipe.recipe_sha256, recipe.recipe_format_version
                FROM {schema}.MODEL_RUN AS run
                LEFT JOIN {schema}.MODEL_RECIPE AS recipe
                  ON recipe.recipe_id=run.recipe_id AND recipe.model_id=run.model_id
                WHERE run.model_run_id=:run"""),
            {"run": model_run_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise RecipeError("baseline model run has no SQL recipe record")
    return row


def inherit_run_recipe(connection, *, model_run_id, model_config) -> RecipeCapture:
    """Carry the declared SQL definition into a refit, including unavailable status.

    Runtime freeze controls and the absence of another CV run belong to the fit
    evidence. They do not change this definition's revision.
    """
    row = _run_recipe(connection, model_run_id)
    if row["recipe_status"] != "CAPTURED":
        return RecipeCapture(
            status=row["recipe_status"], unavailable_reason=row["recipe_unavailable_reason"]
        )
    document = RecipeDocument(
        **json.loads(row["recipe_json"]),
        name=model_config.model_name,
        label=model_config.model_label,
        model_type=model_config.model_type,
        deployment_slot=model_config.deployment_slot,
    )
    capture = RecipeCapture.captured(document)
    validate_recipe_capture(row, capture)
    return capture


def validate_inherited_recipe(connection, *, model_run_id, capture):
    """A monitoring publication must keep its baseline's declared recipe."""
    row = _run_recipe(connection, model_run_id)
    validate_recipe_capture(row, capture)
    if row["recipe_unavailable_reason"] != capture.unavailable_reason:
        raise RecipeError("monitoring recipe availability differs from its baseline")


def resolve_recipe(
    connection, *, model_id: int, recipe: ModelRecipe, created_by: str
) -> StoredRecipe:
    """Reuse identical canonical content or allocate the model's next recipe revision.

    Acquire the model lock and write within the caller's transaction.
    """

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
        validate_recipe_content(row, recipe=recipe)
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
