import json
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from pricing_pipeline import notebook as api
from pricing_pipeline.modeling.recipes import ModelRecipe
from pricing_pipeline.publishing.recipes import resolve_recipe


def test_recipe_allocation_reuses_and_reverts(fitted_case):
    pricing, model, candidate, _ = fitted_case
    recipe = candidate.recipe
    with pricing.engine.begin() as connection:
        first = resolve_recipe(
            connection, model_id=model.model_id, recipe=recipe, created_by="test"
        )
        assert (
            resolve_recipe(connection, model_id=model.model_id, recipe=recipe, created_by="test")
            == first
        )
        changed = ModelRecipe(recipe.document.model_copy(update={"fit_mode": "fit"}))
        second = resolve_recipe(
            connection, model_id=model.model_id, recipe=changed, created_by="test"
        )
        assert second.recipe_revision == first.recipe_revision + 1
        assert (
            resolve_recipe(connection, model_id=model.model_id, recipe=recipe, created_by="test")
            == first
        )


def test_publication_links_recipe_and_does_not_deploy(fitted_case):
    pricing, _, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    assert saved.recipe_revision == 1
    assert saved.recipe_status == "CAPTURED"
    assert saved.recipe_sha256 == candidate.recipe.sha256
    retry = api.save_model_version(pricing, candidate)
    assert retry.recipe_revision == saved.recipe_revision
    with pricing.engine.connect() as c:
        row = c.execute(text("SELECT * FROM pricing.MODEL_RECIPE")).mappings().one()
        assert row["recipe_json"] == candidate.recipe.canonical_json
        assert "name" not in json.loads(row["recipe_json"])
        assert (
            c.execute(text("SELECT COUNT(*) FROM pricing.PRICING_MODEL_DEPLOYMENT")).scalar_one()
            == 0
        )
        assert (
            c.execute(text("SELECT recipe_id FROM pricing.MODEL_RUN")).scalar_one()
            == row["recipe_id"]
        )


def test_recipe_allocation_rolls_back(fitted_case):
    pricing, model, candidate, _ = fitted_case
    with pytest.raises(RuntimeError, match="abort"), pricing.engine.begin() as c:
        resolve_recipe(c, model_id=model.model_id, recipe=candidate.recipe, created_by="test")
        raise RuntimeError("abort")
    with pricing.engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RECIPE")).scalar_one() == 0


def test_recipe_and_published_link_are_immutable(fitted_case):
    pricing, _, candidate, _ = fitted_case
    api.save_model_version(pricing, candidate)
    for sql in [
        "UPDATE pricing.MODEL_RECIPE SET recipe_revision=2",
        "DELETE FROM pricing.MODEL_RECIPE",
        "UPDATE pricing.MODEL_RUN SET recipe_status='LEGACY', recipe_id=NULL",
    ]:
        with pytest.raises(IntegrityError), pricing.engine.begin() as c:
            c.execute(text(sql))


def test_new_recipe_same_rates_cannot_reuse_build(fitted_case):
    pricing, model, candidate, glm = fitted_case
    first = api.save_model_version(pricing, candidate)
    spec = replace(model.spec, scoring=("deviance",))
    registered = api.register_model(pricing, spec, source_root=model.source_root)
    other = api.fit_model(
        pricing,
        model=registered,
        frame=api.apply_transforms(spec.dataset.df, spec.transforms),
        superglm_model=glm,
    )
    saved = api.save_model_version(pricing, other)
    assert saved.model_equivalence_sha256 == first.model_equivalence_sha256
    assert saved.recipe_revision == 2
    assert saved.model_run_id != first.model_run_id
    assert not saved.deduplicated


def test_concurrent_same_recipe_publication_reuses_run(fitted_case):
    from concurrent.futures import ThreadPoolExecutor

    pricing, _, candidate, _ = fitted_case
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: api.save_model_version(pricing, candidate), range(2)))
    assert results[0].model_run_id == results[1].model_run_id
    assert results[0].recipe_revision == results[1].recipe_revision == 1
    with pricing.engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM pricing.MODEL_RECIPE")).scalar_one() == 1


def test_same_recipe_different_folds_does_not_reuse_evidence(fitted_case):
    from sklearn.model_selection import KFold

    pricing, model, _, glm = fitted_case
    spec = replace(model.spec, validation=KFold(n_splits=3, shuffle=True, random_state=None))
    registered = api.register_model(pricing, spec, source_root=model.source_root)
    df = api.apply_transforms(spec.dataset.df, spec.transforms)
    one = api.fit_model(pricing, model=registered, frame=df, superglm_model=glm)
    two = api.fit_model(pricing, model=registered, frame=df, superglm_model=glm)
    assert one.recipe.sha256 == two.recipe.sha256
    assert one.completed_build.split_set_id != two.completed_build.split_set_id
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(
            executor.map(lambda candidate: api.save_model_version(pricing, candidate), (one, two))
        )
    assert first.model_equivalence_sha256 == second.model_equivalence_sha256
    assert first.recipe_revision == second.recipe_revision == 1
    assert first.model_run_id != second.model_run_id
    assert not second.deduplicated


def test_sql_canonical_document_reconstructs_configuration(fitted_case):
    pricing, model, candidate, _ = fitted_case
    api.save_model_version(pricing, candidate)
    with pricing.engine.connect() as c:
        stored = json.loads(
            c.execute(text("SELECT recipe_json FROM pricing.MODEL_RECIPE")).scalar_one()
        )
    from pricing_pipeline.modeling.recipes.schema import BINDING_FIELDS, RecipeDocument

    bindings = {key: getattr(model.spec, key) for key in BINDING_FIELDS}
    loaded = ModelRecipe(RecipeDocument(**(stored | bindings)))
    spec, glm = loaded.build(dataset=model.spec.dataset)
    assert ModelRecipe.from_model(glm, spec=spec).sha256 == candidate.recipe.sha256


def test_publication_failure_rolls_back_allocated_recipe(fitted_case, monkeypatch):
    from pricing_pipeline.publishing import sqlite

    pricing, _, candidate, _ = fitted_case
    original = sqlite._insert_local_lineage

    def abort(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("abort after allocation")

    monkeypatch.setattr(sqlite, "_insert_local_lineage", abort)
    with pytest.raises(RuntimeError, match="abort after allocation"):
        api.save_model_version(pricing, candidate)
    with pricing.engine.connect() as c:
        for table in ("MODEL_RECIPE", "MODEL_RUN", "PRICING_RATE_PACKAGE"):
            assert c.execute(text(f"SELECT COUNT(*) FROM pricing.{table}")).scalar_one() == 0


def test_canonical_hash_match_is_checked_for_integrity(fitted_case):
    from pricing_pipeline.modeling.recipes import RecipeError

    pricing, model, candidate, _ = fitted_case
    recipe = candidate.recipe
    with pricing.engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO pricing.MODEL_RECIPE(model_id,recipe_revision,recipe_sha256,recipe_format_version,recipe_json,created_by) VALUES (:model,1,:sha,1,'{}','test')"
            ),
            {"model": model.model_id, "sha": recipe.sha256},
        )
    with pytest.raises(RecipeError, match="integrity"), pricing.engine.begin() as c:
        resolve_recipe(c, model_id=model.model_id, recipe=recipe, created_by="test")


def test_prepublication_reader_separates_legacy_evidence(fitted_case):
    from pricing_pipeline.modeling.recipes import RecipeCapture
    from pricing_pipeline.publishing.identity import find_equivalent_publication

    pricing, _, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    build = candidate.completed_build.model_copy(
        update={"model_equivalence_sha256": saved.model_equivalence_sha256}
    )
    assert find_equivalent_publication(pricing.engine, build=build).recipe_revision == 1
    legacy = build.model_copy(update={"recipe_capture": RecipeCapture()})
    assert find_equivalent_publication(pricing.engine, build=legacy) is None


def test_concurrent_different_recipes_same_rates_keep_both_builds(fitted_case):
    from concurrent.futures import ThreadPoolExecutor

    pricing, model, one, glm = fitted_case
    spec = replace(model.spec, scoring=("deviance",))
    registered = api.register_model(pricing, spec, source_root=model.source_root)
    two = api.fit_model(
        pricing,
        model=registered,
        frame=api.apply_transforms(spec.dataset.df, spec.transforms),
        superglm_model=glm,
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(
            executor.map(lambda candidate: api.save_model_version(pricing, candidate), (one, two))
        )
    assert first.model_equivalence_sha256 == second.model_equivalence_sha256
    assert first.model_run_id != second.model_run_id
    assert {first.recipe_revision, second.recipe_revision} == {1, 2}


def test_unsupported_recipe_cannot_deduplicate_another_export(fitted_case):
    from pricing_pipeline.modeling.recipes import RecipeCapture
    from pricing_pipeline.publishing.identity import find_equivalent_publication

    pricing, _, candidate, _ = fitted_case
    saved = api.save_model_version(pricing, candidate)
    build = candidate.completed_build.model_copy(
        update={
            "model_equivalence_sha256": saved.model_equivalence_sha256,
            "recipe_capture": RecipeCapture(
                status="UNSUPPORTED", unavailable_reason="custom Python splitter"
            ),
        }
    )
    assert find_equivalent_publication(pricing.engine, build=build) is None


@pytest.mark.parametrize("route", ["retry", "equivalent", "preflight"])
def test_corrupt_canonical_content_rejected_on_existing_publication(fitted_case, route):
    from pricing_pipeline.modeling.recipes import RecipeError
    from pricing_pipeline.publishing.identity import find_equivalent_publication

    pricing, model, candidate, glm = fitted_case
    saved = api.save_model_version(pricing, candidate)
    other = (
        api.fit_model(
            pricing,
            model=model,
            frame=api.apply_transforms(model.spec.dataset.df, model.spec.transforms),
            superglm_model=glm,
        )
        if route == "equivalent"
        else candidate
    )
    with pricing.engine.begin() as c:
        c.execute(text("DROP TRIGGER pricing.TR_MODEL_RECIPE_UPDATE"))
        c.execute(text("UPDATE pricing.MODEL_RECIPE SET recipe_json='{}'"))
    with pytest.raises(RecipeError, match="integrity"):
        if route == "preflight":
            find_equivalent_publication(
                pricing.engine,
                build=candidate.completed_build.model_copy(
                    update={"model_equivalence_sha256": saved.model_equivalence_sha256}
                ),
            )
        else:
            api.save_model_version(pricing, other)


@pytest.mark.parametrize("deduplicated", [False, True])
@pytest.mark.parametrize("corruption", [{"recipe_json": "{}"}, {"recipe_format_version": 99}])
def test_sqlserver_existing_returns_validate_full_recipe(fitted_case, deduplicated, corruption):
    from types import SimpleNamespace

    from pricing_pipeline.modeling.recipes import RecipeError
    from pricing_pipeline.publishing import sqlserver

    _, _, candidate, _ = fitted_case
    build = candidate.completed_build
    row = {
        "package_status": "PUBLISHED",
        "model_id": build.model_id,
        "model_name": build.model_name,
        "manifest_id": build.manifest_id,
        "model_kind": build.model_kind,
        "recipe_status": build.recipe_status,
        "recipe_sha256": build.recipe_sha256,
        "split_set_id": build.split_set_id,
        "model_equivalence_sha256": build.model_equivalence_sha256,
        "run_status": "SUCCESS",
        "recipe_json": build.recipe_capture.canonical,
        "recipe_format_version": build.recipe_capture.document.format_version,
    } | corruption

    class Connection:
        def execute(self, statement, params):
            assert "recipe.recipe_json" in str(statement)
            assert "recipe.recipe_format_version" in str(statement)
            return self

        def mappings(self):
            return self

        def all(self):
            return [row]

    with pytest.raises(RecipeError, match="integrity"):
        sqlserver._completed_package(
            Connection(),
            prepared=SimpleNamespace(build=build),
            rate_package_id=1,
            was_existing=True,
            deduplicated=deduplicated,
        )
