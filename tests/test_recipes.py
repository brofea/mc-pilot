"""Recipe data pipeline and algorithm tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from mc_pilot.recipes.downloader import _sha1_hex, find_release_version
from mc_pilot.recipes.extractor import parse_recipe
from mc_pilot.recipes.models import (
    DirectRecipeResponse,
    Ingredient,
    MaterialNode,
    RecipeInfo,
    RecipeTreeResponse,
    VersionMetadata,
)
from mc_pilot.recipes.store import (
    clear_version_data,
    load_item_names,
    load_recipes,
    load_tags,
    store_items,
    store_recipes,
    store_tags,
)
from mc_pilot.recipes.tree import RecipeTreeEngine
from mc_pilot.storage.sqlite import create_sqlite_engine, initialize_database

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict[str, object]:
    path = FIXTURES_DIR / name
    data: dict[str, object] = json.loads(path.read_text())
    return data


def _make_recipe_from_fixture(key: str) -> RecipeInfo | None:
    data = _load_fixture("sample_recipes.json")
    raw = data[key]
    assert isinstance(raw, dict)
    recipe = parse_recipe(raw)
    if recipe is None:
        return None
    return RecipeInfo(
        recipe_id=recipe.recipe_id,
        recipe_type=recipe.recipe_type,
        group=recipe.group,
        result_item_id=recipe.result_item_id,
        result_count=recipe.result_count,
        category=recipe.category,
        ingredients=recipe.ingredients,
        version_id="26.2",
    )


# ── Parser tests ──────────────────────────────────────────────────────


def test_parse_shaped_recipe() -> None:
    recipe = _make_recipe_from_fixture("shaped_enchanting_table")
    assert recipe is not None
    assert recipe.recipe_id == "enchanting_table"
    assert recipe.recipe_type == "minecraft:crafting_shaped"
    assert recipe.result_item_id == "minecraft:enchanting_table"
    assert recipe.result_count == 1
    assert recipe.category == "misc"
    assert len(recipe.ingredients) == 3
    item_ids = {ing.item_id for ing in recipe.ingredients}
    assert item_ids == {"minecraft:obsidian", "minecraft:book", "minecraft:diamond"}


def test_parse_shapeless_recipe() -> None:
    recipe = _make_recipe_from_fixture("shapeless_flint_and_steel")
    assert recipe is not None
    assert recipe.recipe_type == "minecraft:crafting_shapeless"
    assert recipe.result_item_id == "minecraft:flint_and_steel"
    assert len(recipe.ingredients) == 2


def test_parse_tag_ingredient() -> None:
    recipe = _make_recipe_from_fixture("shaped_crafting_table")
    assert recipe is not None
    tags = [ing for ing in recipe.ingredients if ing.ingredient_kind == "tag"]
    assert len(tags) == 1
    assert tags[0].tag == "minecraft:planks"


def test_parse_empty_pattern_handled() -> None:
    recipe = _make_recipe_from_fixture("empty_pattern_recipe")
    assert recipe is not None
    assert recipe.result_item_id == "minecraft:iron_nugget"
    assert recipe.result_count == 9
    assert len(recipe.ingredients) == 0


def test_parse_smelting_recipe() -> None:
    recipe = _make_recipe_from_fixture("smelting_iron_ingot")
    assert recipe is not None
    assert recipe.recipe_type == "minecraft:smelting"
    assert recipe.result_item_id == "minecraft:iron_ingot"
    assert len(recipe.ingredients) == 1
    assert recipe.ingredients[0].item_id == "minecraft:raw_iron"


def test_parse_stonecutting_recipe() -> None:
    recipe = _make_recipe_from_fixture("stonecutting_quartz_slab")
    assert recipe is not None
    assert recipe.result_count == 2
    assert recipe.ingredients[0].item_id == "minecraft:quartz_block"


def test_parse_invalid_input_returns_none() -> None:
    assert parse_recipe({}) is None
    assert parse_recipe({"type": "minecraft:custom_unknown"}) is None
    assert parse_recipe({"type": "minecraft:crafting_shaped"}) is None


# ── Tree algorithm tests ───────────────────────────────────────────────


def _build_engine(items: dict[str, str] | None = None) -> RecipeTreeEngine:
    data = _load_fixture("sample_recipes.json")
    recipes: dict[str, list[RecipeInfo]] = {}
    for _key, raw in data.items():
        assert isinstance(raw, dict)
        parsed = parse_recipe(raw)
        if parsed is None:
            continue
        info = RecipeInfo(
            recipe_id=parsed.recipe_id,
            recipe_type=parsed.recipe_type,
            group=parsed.group,
            result_item_id=parsed.result_item_id,
            result_count=parsed.result_count,
            category=parsed.category,
            ingredients=parsed.ingredients,
            version_id="26.2",
        )
        recipes.setdefault(parsed.result_item_id, []).append(info)
    return RecipeTreeEngine(
        recipes=recipes,
        item_names=items or {},
        tags={"minecraft:planks": ["minecraft:oak_planks", "minecraft:spruce_planks"]},
        version_id="26.2",
    )


def test_direct_recipe_lookup_by_item_id() -> None:
    engine = _build_engine()
    result = engine.direct_recipes("minecraft:enchanting_table")
    assert len(result) == 1
    assert result[0].recipe_id == "enchanting_table"


def test_direct_recipe_missing_returns_empty() -> None:
    engine = _build_engine()
    result = engine.direct_recipes("minecraft:netherite_block")
    assert result == []


def test_build_single_level_tree() -> None:
    engine = _build_engine()
    result = engine.build_tree("minecraft:flint_and_steel", target_quantity=1)

    assert not result.truncated
    children = result.root.children
    assert len(children) == 2
    child_ids = {c.item_id for c in children}
    assert child_ids == {"minecraft:iron_ingot", "minecraft:flint"}
    # iron_ingot has a smelting recipe, so it's not a leaf
    flint_child = next(c for c in children if c.item_id == "minecraft:flint")
    assert flint_child.is_leaf
    iron_child = next(c for c in children if c.item_id == "minecraft:iron_ingot")
    assert not iron_child.is_leaf


def test_build_tree_with_tags() -> None:
    items = {
        "minecraft:crafting_table": "Crafting Table",
        "minecraft:oak_planks": "Oak Planks",
        "minecraft:spruce_planks": "Spruce Planks",
    }
    engine = _build_engine(items)
    result = engine.build_tree("minecraft:crafting_table", target_quantity=1)

    assert not result.truncated
    assert result.root.recipe_id is not None
    children = result.root.children
    assert len(children) == 1
    tag_node = children[0]
    assert "#" in tag_node.display_name
    assert len(tag_node.children) == 2


def test_build_tree_with_quantity_scaling() -> None:
    engine = _build_engine()
    result = engine.build_tree("minecraft:iron_nugget", target_quantity=3)

    assert result.root.is_leaf
    assert result.leaf_totals["minecraft:iron_nugget"] == 3


def test_cycle_detection() -> None:
    items = {"minecraft:plank_loop": "Plank Loop"}
    recipes = {
        "minecraft:plank_loop": [
            RecipeInfo(
                recipe_id="plank_loop",
                recipe_type="minecraft:crafting_shaped",
                result_item_id="minecraft:plank_loop",
                result_count=1,
                ingredients=(
                    Ingredient(ingredient_kind="item", item_id="minecraft:plank_loop"),
                ),
                version_id="26.2",
            )
        ]
    }
    engine = RecipeTreeEngine(recipes=recipes, item_names=items, version_id="26.2")
    result = engine.build_tree("minecraft:plank_loop")

    assert result.truncated
    assert result.truncation_reason is not None
    assert "Cycle" in result.truncation_reason or "cycle" in result.truncation_reason


def test_max_depth_truncation() -> None:
    items = {
        "minecraft:deep_item": "Deep Item",
        "minecraft:intermediate": "Intermediate",
    }
    recipes = {
        "minecraft:deep_item": [
            RecipeInfo(
                recipe_id="deep_item",
                recipe_type="minecraft:crafting_shaped",
                result_item_id="minecraft:deep_item",
                result_count=1,
                ingredients=(
                    Ingredient(ingredient_kind="item", item_id="minecraft:intermediate"),
                ),
                version_id="26.2",
            )
        ],
        "minecraft:intermediate": [
            RecipeInfo(
                recipe_id="intermediate",
                recipe_type="minecraft:crafting_shaped",
                result_item_id="minecraft:intermediate",
                result_count=1,
                ingredients=(
                    Ingredient(ingredient_kind="item", item_id="minecraft:deep_item"),
                ),
                version_id="26.2",
            )
        ],
    }
    engine = RecipeTreeEngine(recipes=recipes, item_names=items, version_id="26.2")
    result = engine.build_tree("minecraft:deep_item", max_depth=0)

    assert result.root.is_leaf
    assert result.root.depth == 0


def test_leaf_totals_accumulate() -> None:
    engine = _build_engine()
    result = engine.build_tree("minecraft:flint_and_steel", target_quantity=2)

    assert "minecraft:raw_iron" in result.leaf_totals
    assert "minecraft:flint" in result.leaf_totals
    assert result.leaf_totals["minecraft:raw_iron"] == 2
    assert result.leaf_totals["minecraft:flint"] == 2


def test_recipe_tree_response_structure() -> None:
    response = RecipeTreeResponse(
        target_item_id="minecraft:diamond_sword",
        target_quantity=1,
        tree=MaterialNode(
            item_id="minecraft:diamond_sword",
            quantity=1,
            depth=0,
            is_leaf=False,
            children=(),
        ),
        leaf_totals={},
        total_nodes=1,
        version_id="26.2",
    )
    assert response.truncated is False
    assert response.truncation_reason is None


# ── Version finder tests ───────────────────────────────────────────────


def test_find_release_version_match() -> None:
    versions = [
        VersionMetadata(
            version_id="26.2",
            release_type="release",
            manifest_url="https://example.com/26.2.json",
        ),
        VersionMetadata(
            version_id="26.3",
            release_type="snapshot",
            manifest_url="https://example.com/26.3.json",
        ),
    ]
    result = find_release_version(versions, "26.2")
    assert result is not None
    assert result.version_id == "26.2"
    assert result.release_type == "release"


def test_find_release_version_snapshot_not_matched() -> None:
    versions = [
        VersionMetadata(
            version_id="26.2",
            release_type="snapshot",
            manifest_url="https://example.com/26.2.json",
        )
    ]
    result = find_release_version(versions, "26.2")
    assert result is None


def test_find_release_version_missing() -> None:
    result = find_release_version([], "26.2")
    assert result is None


# ── SHA-1 utility tests ────────────────────────────────────────────────


def test_sha1_hex_known_content(tmp_path: Path) -> None:
    content = b"minecraft recipe test data"
    path = tmp_path / "test.bin"
    path.write_bytes(content)
    expected = hashlib.sha1(content).hexdigest()
    assert _sha1_hex(path) == expected


def test_sha1_hex_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.bin"
    path.write_bytes(b"")
    expected = hashlib.sha1(b"").hexdigest()
    assert _sha1_hex(path) == expected


# ── SQLite store tests ─────────────────────────────────────────────────


class TestStore:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path) -> None:
        self._db_path = tmp_path / "test_recipes.db"
        self._engine = create_sqlite_engine(f"sqlite:///{self._db_path}")
        initialize_database(self._engine)

    def _session(self) -> Session:
        return Session(self._engine)

    def test_store_and_load_items(self) -> None:
        items = {"minecraft:stone": "Stone", "minecraft:dirt": "Dirt"}
        with self._session() as session:
            store_items(session, items, "26.2")
            loaded = load_item_names(session, "26.2")

        assert loaded == items

    def test_store_and_load_recipes(self) -> None:
        recipe = RecipeInfo(
            recipe_id="test_recipe",
            recipe_type="minecraft:crafting_shaped",
            result_item_id="minecraft:stone",
            result_count=1,
            ingredients=(
                Ingredient(ingredient_kind="item", item_id="minecraft:cobblestone"),
            ),
            version_id="26.2",
        )
        with self._session() as session:
            store_recipes(session, [recipe], "26.2")
            loaded = load_recipes(self._session(), "26.2")

        assert "minecraft:stone" in loaded
        assert len(loaded["minecraft:stone"]) == 1
        assert loaded["minecraft:stone"][0].recipe_id == "test_recipe"

    def test_store_and_load_tags(self) -> None:
        tags = {"minecraft:planks": ["minecraft:oak_planks", "minecraft:spruce_planks"]}
        with self._session() as session:
            store_tags(session, tags, "26.2")
            loaded = load_tags(self._session(), "26.2")

        assert "minecraft:planks" in loaded
        assert set(loaded["minecraft:planks"]) == {
            "minecraft:oak_planks",
            "minecraft:spruce_planks",
        }

    def test_clear_version_data(self) -> None:
        items = {"minecraft:stone": "Stone"}
        with self._session() as session:
            store_items(session, items, "26.2")
            store_items(session, items, "26.1")

        with self._session() as session:
            clear_version_data(session, "26.2")

        with self._session() as session:
            loaded_26_2 = load_item_names(session, "26.2")
            loaded_26_1 = load_item_names(session, "26.1")

        assert loaded_26_2 == {}
        assert loaded_26_1 == items

    def test_load_empty_returns_empty(self) -> None:
        with self._session() as session:
            assert load_recipes(session, "99.9") == {}
            assert load_item_names(session, "99.9") == {}
            assert load_tags(session, "99.9") == {}


# ── Model validation tests ─────────────────────────────────────────────


def test_ingredient_model_validation() -> None:
    ing = Ingredient(ingredient_kind="item", item_id="minecraft:stone")
    assert ing.count == 1

    tag = Ingredient(ingredient_kind="tag", tag="minecraft:planks")
    assert tag.tag == "minecraft:planks"


def test_recipe_info_immutable() -> None:
    recipe = RecipeInfo(
        recipe_id="abc",
        recipe_type="minecraft:crafting_shaped",
        result_item_id="minecraft:stone",
    )
    assert recipe.recipe_id == "abc"
    assert recipe.model_config.get("frozen") is True


def test_direct_recipe_response_defaults() -> None:
    response = DirectRecipeResponse(item_id="minecraft:stone")
    assert response.total_recipes == 0
    assert response.recipes == ()
    assert response.version_id == ""
