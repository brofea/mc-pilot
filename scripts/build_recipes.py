#!/usr/bin/env python3
"""Download, extract, and build the official recipe database for a given version."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from mc_pilot.config import get_settings
from mc_pilot.recipes.service import RecipeService
from mc_pilot.storage.sqlite import create_sqlite_engine

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local recipe database from Mojang CDN.")
    parser.add_argument(
        "--version",
        default="26.2",
        help="Minecraft version ID (must be 'release' type). Default: 26.2",
    )
    parser.add_argument(
        "--cache-dir",
        default="data/recipes/cache",
        help="Directory to cache downloaded JARs.",
    )
    parser.add_argument(
        "--mirror",
        action="append",
        default=[],
        help="Mirror URL for fallback download (repeatable).",
    )
    parser.add_argument(
        "--no-mirror",
        action="store_true",
        help="Disable all mirror URLs.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    settings = get_settings()
    engine = create_sqlite_engine(settings.sqlite_url)

    from mc_pilot.storage.sqlite import initialize_database

    initialize_database(engine)

    mirrors: tuple[str, ...] = ()
    if not args.no_mirror and args.mirror:
        mirrors = tuple(args.mirror)

    service = RecipeService(engine=engine, version_id=args.version)
    result = await service.acquire_and_build(
        cache_dir=Path(args.cache_dir),
        mirror_urls=mirrors,
    )

    logger.info(
        "Recipe build finished",
        extra={
            "recipes": result.recipe_count,
            "tags": len(result.tags),
            "items": result.item_count,
        },
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_main())
