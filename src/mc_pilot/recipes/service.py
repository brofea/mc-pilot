"""High-level recipe service that orchestrates acquisition, parsing, and queries."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mc_pilot.recipes.downloader import (
    DownloaderConfig,
    download_jar,
    fetch_version_detail,
    fetch_version_manifest,
    find_release_version,
)
from mc_pilot.recipes.extractor import ExtractionResult, extract_jar_data, parse_recipe
from mc_pilot.recipes.models import (
    DirectRecipeResponse,
    MaterialNode,
    RecipeInfo,
    RecipeTreeResponse,
)
from mc_pilot.recipes.store import (
    clear_version_data,
    count_recipes,
    load_item_names,
    load_recipes,
    load_tags,
    store_items,
    store_recipes,
    store_tags,
)
from mc_pilot.recipes.tree import RecipeTreeEngine

logger = logging.getLogger(__name__)


class RecipeService:
    """Orchestrates recipe data pipeline and query operations."""

    _engine: Engine
    _version_id: str

    def __init__(self, engine: Engine, version_id: str = "26.2") -> None:
        self._engine = engine
        self._version_id = version_id

    @property
    def version_id(self) -> str:
        return self._version_id

    async def acquire_and_build(
        self,
        cache_dir: Path | None = None,
        mirror_urls: tuple[str, ...] = (),
    ) -> ExtractionResult:
        """Full pipeline: download, verify, extract, parse, and store."""
        import httpx

        cache = cache_dir or Path("data/recipes/cache")
        config = DownloaderConfig(cache_dir=cache, mirror_urls=mirror_urls)

        async with httpx.AsyncClient() as client:
            versions = await fetch_version_manifest(client)
            target = find_release_version(versions, self._version_id)
            if not target:
                available = [v.version_id for v in versions if v.release_type == "release"]
                raise ValueError(
                    f"Version {self._version_id} not found in release manifest. "
                    f"Available releases: {sorted(available)[-5:]}"
                )

            detail = await fetch_version_detail(client, target)
            logger.info(
                "Resolved version detail",
                extra={
                    "version": detail.version_id,
                    "sha1": detail.client_sha1,
                    "size": detail.client_size,
                },
            )

        download_result = await download_jar(detail, config=config)
        if not download_result.sha1_match:
            raise ValueError("SHA-1 verification failed — aborting import")

        logger.info("Extracting JAR data", extra={"path": str(download_result.file_path)})
        extracted = extract_jar_data(download_result.file_path)

        recipes: list[RecipeInfo] = []
        skipped = 0
        for raw_recipe in extracted.recipes:
            parsed = parse_recipe(raw_recipe)
            if parsed is not None:
                updated = RecipeInfo(
                    recipe_id=parsed.recipe_id,
                    recipe_type=parsed.recipe_type,
                    group=parsed.group,
                    result_item_id=parsed.result_item_id,
                    result_count=parsed.result_count,
                    category=parsed.category,
                    ingredients=parsed.ingredients,
                    version_id=self._version_id,
                )
                recipes.append(updated)
            else:
                skipped += 1

        logger.info(
            "Parsed recipes",
            extra={
                "parsed": len(recipes),
                "skipped": skipped,
            },
        )

        item_names: dict[str, str] = {}
        for _, lang_data in extracted.localizations.items():
            for key, value in lang_data.items():
                if key.startswith(("block.", "item.")):
                    item_names[key] = value

        for raw_recipe in extracted.recipes:
            result_key = raw_recipe.get("result")
            result_id: str | None = None
            if isinstance(result_key, dict):
                result_id = result_key.get("id") or result_key.get("item")
            elif isinstance(result_key, str):
                result_id = result_key
            if result_id and result_id not in item_names:
                item_names[result_id] = result_id

        tags_for_storage = _normalize_tags(extracted.tags, self._version_id)

        with Session(self._engine) as session:
            clear_version_data(session, self._version_id)
            store_items(session, item_names, self._version_id)
            store_recipes(session, recipes, self._version_id)
            store_tags(session, tags_for_storage, self._version_id)

        logger.info(
            "Recipe build complete",
            extra={
                "version": self._version_id,
                "recipes": len(recipes),
                "items": len(item_names),
                "tags": len(tags_for_storage),
            },
        )
        return extracted

    def query_direct(self, item_id: str) -> DirectRecipeResponse:
        engine = self._get_engine()
        with Session(engine) as session:
            items = load_item_names(session, self._version_id)
            recipes = load_recipes(session, self._version_id)

        matches = recipes.get(item_id, [])
        return DirectRecipeResponse(
            item_id=item_id,
            display_name=items.get(item_id, item_id),
            recipes=tuple(matches),
            total_recipes=len(matches),
            version_id=self._version_id,
        )

    def query_tree(
        self,
        item_id: str,
        quantity: int = 1,
        max_depth: int | None = None,
        recipe_selections: dict[str, str] | None = None,
    ) -> RecipeTreeResponse:
        engine = self._get_engine()
        with Session(engine) as session:
            items = load_item_names(session, self._version_id)
            recipes = load_recipes(session, self._version_id)
            tags = load_tags(session, self._version_id)

        if item_id not in recipes:
            return RecipeTreeResponse(
                target_item_id=item_id,
                target_display_name=items.get(item_id, item_id),
                target_quantity=quantity,
                max_depth=max_depth,
                tree=MaterialNode(
                    item_id=item_id,
                    display_name=items.get(item_id, item_id),
                    quantity=quantity,
                    depth=0,
                    is_leaf=True,
                ),
                leaf_totals={item_id: quantity},
                total_nodes=1,
                version_id=self._version_id,
            )

        engine_tree = RecipeTreeEngine(
            recipes=recipes,
            item_names=items,
            tags=tags,
            version_id=self._version_id,
        )

        result = engine_tree.build_tree(
            target_item_id=item_id,
            target_quantity=quantity,
            max_depth=max_depth,
            recipe_selections=recipe_selections,
        )

        return RecipeTreeResponse(
            target_item_id=item_id,
            target_display_name=items.get(item_id, item_id),
            target_quantity=quantity,
            max_depth=max_depth,
            tree=result.root,
            leaf_totals=result.leaf_totals,
            truncated=result.truncated,
            truncation_reason=result.truncation_reason,
            total_nodes=result.total_nodes,
            version_id=self._version_id,
        )

    def _get_engine(self) -> Engine:
        return self._engine

    def get_stats(self) -> dict[str, object]:
        """Return recipe database statistics."""
        try:
            with Session(self._engine) as session:
                counts = count_recipes(session, self._version_id)
            return {
                "available": True,
                "version_id": self._version_id,
                "recipe_count": counts["recipes"],
                "item_count": counts["items"],
                "tag_count": counts["tags"],
            }
        except Exception as exc:
            logger.warning("Failed to get recipe stats", extra={"error": str(exc)})
            return {"available": False, "version_id": self._version_id, "error": str(exc)}


def _normalize_tags(
    tags: dict[str, list[str]],
    version_id: str,
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for tag_name, items in tags.items():
        cleaned = [item for item in items if item.startswith("minecraft:")]
        if cleaned:
            out[tag_name] = cleaned
    return out
