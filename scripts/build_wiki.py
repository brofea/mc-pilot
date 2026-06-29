#!/usr/bin/env python3
"""Collect Chinese Wiki pages, embed with BGE-small-zh, and index into Qdrant."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from mc_pilot.config import get_settings
from mc_pilot.rag.service import WikiService

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Chinese Minecraft Wiki RAG index."
    )
    parser.add_argument(
        "--cache-dir",
        default="data/wiki/cache",
        help="Directory for API response cache.",
    )
    parser.add_argument(
        "--api-url",
        default="https://zh.minecraft.wiki/api.php",
        help="MediaWiki API endpoint.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    settings = get_settings()
    service = WikiService(
        qdrant_url=settings.qdrant_url,
        api_url=args.api_url,
        cache_dir=Path(args.cache_dir),
    )

    metadata = await service.build_index()
    logger.info(
        "Wiki index built",
        extra={
            "pages": metadata.page_count,
            "chunks": metadata.chunk_count,
            "dimension": metadata.embedding_dimension,
        },
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_main())
