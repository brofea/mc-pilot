"""Extract recipe JSON, item tags, and localisation from a Minecraft JAR."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from mc_pilot.recipes.models import Ingredient, RecipeInfo

logger = logging.getLogger(__name__)

RECIPE_PATH_PREFIX = "data/minecraft/recipe/"
TAG_PATH_PREFIX = "data/minecraft/tags/"


@dataclass
class ExtractionResult:
    recipes: list[dict[str, Any]] = field(default_factory=list)
    tags: dict[str, list[str]] = field(default_factory=dict)
    localizations: dict[str, dict[str, str]] = field(default_factory=dict)
    recipe_count: int = 0
    tag_count: int = 0
    item_count: int = 0


def extract_jar_data(jar_path: Path) -> ExtractionResult:
    """Extract recipes, tags, and localizations from a Minecraft JAR."""
    if not jar_path.exists():
        raise FileNotFoundError(f"JAR not found: {jar_path}")

    result = ExtractionResult()

    with ZipFile(jar_path, "r") as zf:
        resource_names = zf.namelist()
        _extract_recipes(zf, resource_names, result)
        _extract_tags(zf, resource_names, result)
        _extract_localizations(zf, resource_names, result)

    result.recipe_count = len(result.recipes)
    logger.info(
        "JAR extraction complete",
        extra={
            "recipes": result.recipe_count,
            "tags": result.tag_count,
            "items": result.item_count,
        },
    )
    return result


def _extract_recipes(
    zf: ZipFile,
    resource_names: list[str],
    result: ExtractionResult,
) -> None:
    for name in resource_names:
        if not (name.startswith(RECIPE_PATH_PREFIX) and name.endswith(".json")):
            continue
        try:
            raw = json.loads(zf.read(name).decode("utf-8"))
            raw["_file"] = name
            result.recipes.append(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning(
                "Failed to parse recipe JSON", extra={"file": name, "error": str(exc)}
            )


def _extract_tags(
    zf: ZipFile,
    resource_names: list[str],
    result: ExtractionResult,
) -> None:
    for name in resource_names:
        if not (name.startswith(TAG_PATH_PREFIX) and name.endswith(".json")):
            continue
        tag_name = name.removeprefix(TAG_PATH_PREFIX).removesuffix(".json")
        tag_name = tag_name.replace("/", ":")
        if tag_name.count(":") == 1:
            tag_name = f"minecraft:{tag_name}"
        try:
            raw = json.loads(zf.read(name).decode("utf-8"))
            items: list[str] = []
            if isinstance(raw, dict) and "values" in raw:
                for entry in raw.get("values", []):
                    if isinstance(entry, str):
                        items.append(entry)
                    elif isinstance(entry, dict) and "id" in entry:
                        items.append(entry["id"])
            elif isinstance(raw, list):
                items = [str(e) for e in raw]
            if items:
                result.tags[tag_name] = items
                result.tag_count += len(items)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning(
                "Failed to parse tag JSON", extra={"file": name, "error": str(exc)}
            )


def _extract_localizations(
    zf: ZipFile,
    resource_names: list[str],
    result: ExtractionResult,
) -> None:
    lang_patterns = (
        "assets/minecraft/lang/zh_cn.json",
        "assets/minecraft/lang/en_us.json",
    )
    for pattern in lang_patterns:
        if pattern not in resource_names:
            logger.debug("Localization file not found in JAR", extra={"pattern": pattern})
            continue
        try:
            raw = json.loads(zf.read(pattern).decode("utf-8"))
            lang_key = Path(pattern).stem
            result.localizations[lang_key] = raw
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning(
                "Failed to parse localization JSON",
                extra={"file": pattern, "error": str(exc)},
            )


def parse_recipe(raw: dict[str, Any]) -> RecipeInfo | None:
    """Parse a raw recipe JSON dict into a RecipeInfo domain model."""
    recipe_type = raw.get("type", "")
    if not recipe_type:
        return None

    result_key = raw.get("result")
    result_item_id: str | None = None
    result_count: int = 1

    if isinstance(result_key, dict):
        result_item_id = result_key.get("id") or result_key.get("item") or ""
        result_count = result_key.get("count", 1)
    elif isinstance(result_key, str):
        result_item_id = result_key
        result_count = 1

    if not result_item_id:
        return None

    recipe_id = (
        raw.get("_file", "").removeprefix(RECIPE_PATH_PREFIX).removesuffix(".json")
    )
    group = raw.get("group")
    category = raw.get("category")

    ingredients: list[Ingredient] = []
    if recipe_type == "minecraft:crafting_shaped":
        _parse_shaped_ingredients(raw, ingredients)
    elif recipe_type in (
        "minecraft:crafting_shapeless",
        "minecraft:crafting_special_firework_rocket",
        "minecraft:crafting_special_firework_star",
        "minecraft:crafting_special_firework_star_fade",
        "minecraft:crafting_special_suspiciousstew",
    ):
        _parse_shapeless_ingredients(raw, ingredients)
    elif recipe_type == "minecraft:smelting":
        _parse_cooking_ingredients(raw, ingredients)
    elif recipe_type == "minecraft:stonecutting":
        _parse_cutting_ingredients(raw, ingredients)
    else:
        return None

    return RecipeInfo(
        recipe_id=recipe_id,
        recipe_type=recipe_type,
        group=group,
        result_item_id=result_item_id,
        result_count=result_count,
        category=category,
        ingredients=tuple(ingredients),
    )


def _parse_shaped_ingredients(
    raw: dict[str, Any], ingredients: list[Ingredient]
) -> None:
    key_map: dict[str, dict[str, Any]] = raw.get("key", {})
    pattern: list[str] = raw.get("pattern", [])
    seen_keys: set[str] = set()

    for _row_idx, row in enumerate(pattern):
        for _col_idx, ch in enumerate(row):
            if ch == " ":
                continue
            if ch in seen_keys:
                continue
            seen_keys.add(ch)

            entry = key_map.get(ch, {})
            if isinstance(entry, list):
                entry = entry[0] if entry else {}
            _append_ingredient_from_entry(entry, ingredients, ch, len(ingredients))


def _parse_shapeless_ingredients(
    raw: dict[str, Any], ingredients: list[Ingredient]
) -> None:
    entries: list[object] = raw.get("ingredients", [])
    for idx, entry in enumerate(entries):
        _append_ingredient_from_entry(entry, ingredients, None, idx)


def _parse_cooking_ingredients(
    raw: dict[str, Any], ingredients: list[Ingredient]
) -> None:
    entry = raw.get("ingredient", {})
    if isinstance(entry, list):
        entry = entry[0] if entry else {}
    _append_ingredient_from_entry(entry, ingredients, None, 0)


def _parse_cutting_ingredients(
    raw: dict[str, Any], ingredients: list[Ingredient]
) -> None:
    entry = raw.get("ingredient", {})
    _append_ingredient_from_entry(entry, ingredients, None, 0)


def _append_ingredient_from_entry(
    entry: object,
    ingredients: list[Ingredient],
    slot_key: str | None,
    position: int,
) -> None:
    # Minecraft 26.2 represents some ingredient alternatives as a list. The
    # current domain model stores one representative per slot, matching the
    # pre-existing shaped/cooking behavior until alternatives become a
    # first-class recipe-tree concept.
    if isinstance(entry, list):
        entry = entry[0] if entry else {}
    if isinstance(entry, str):
        entry = {"item": entry}
    if not isinstance(entry, dict):
        return

    item_id = entry.get("item") or entry.get("id")
    tag = entry.get("tag")

    if not item_id and not tag:
        return

    kind = "tag" if tag else "item"
    ingredients.append(
        Ingredient(
            ingredient_kind=kind,
            item_id=item_id,
            tag=tag,
            count=1,
            slot_key=slot_key,
        )
    )
