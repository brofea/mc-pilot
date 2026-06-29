"""MediaWiki API client with pagination, retry, throttle, and disk cache."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://zh.minecraft.wiki/api.php"
DEFAULT_THROTTLE_SECONDS = 1.0
DEFAULT_PAGE_SIZE = 50
MAX_RETRIES = 3


class WikiClient:
    """Async MediaWiki API wrapper with caching and backoff."""

    _client: httpx.AsyncClient
    _api_url: str
    _cache_dir: Path | None
    _throttle_seconds: float

    def __init__(
        self,
        api_url: str = DEFAULT_API_URL,
        cache_dir: Path | None = None,
        throttle_seconds: float = DEFAULT_THROTTLE_SECONDS,
    ) -> None:
        self._api_url = api_url
        self._cache_dir = cache_dir
        self._throttle_seconds = throttle_seconds
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "MinecraftPilot/0.1 (research project)"},
        )
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    async def close(self) -> None:
        await self._client.aclose()

    async def category_members(
        self,
        category: str,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        continue_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": category if category.startswith("Category:") else f"Category:{category}",
            "cmlimit": min(limit, 500),
            "cmtype": "page",
        }
        if continue_token:
            params["cmcontinue"] = continue_token
        return await self._fetch(params)

    async def page_content(self, page_ids: list[int]) -> dict[str, Any]:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "prop": "revisions|info",
            "rvprop": "content|ids",
            "rvslots": "main",
            "inprop": "url",
            "pageids": "|".join(str(pid) for pid in page_ids),
        }
        return await self._fetch(params)

    async def page_info(self, titles: list[str]) -> dict[str, Any]:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "prop": "info|pageprops",
            "inprop": "url",
            "titles": "|".join(titles),
        }
        return await self._fetch(params)

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        namespace: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "srnamespace": namespace,
        }
        return await self._fetch(params)

    async def _fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        cache_key = self._cache_key(params)
        if self._cache_dir:
            cached = self._load_cache(cache_key)
            if cached is not None:
                return cached

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.get(self._api_url, params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                if self._cache_dir:
                    self._save_cache(cache_key, data)
                return data
            except httpx.HTTPError as exc:
                logger.warning(
                    "Wiki API request failed",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                if attempt >= MAX_RETRIES:
                    raise RuntimeError(
                        f"Wiki API request failed after {MAX_RETRIES} attempts"
                    ) from exc
                import asyncio

                await asyncio.sleep(2.0**attempt)
        raise RuntimeError("Unreachable")

    def _cache_key(self, params: dict[str, Any]) -> str:
        raw = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest() + ".json"

    def _load_cache(self, key: str) -> dict[str, Any] | None:
        if not self._cache_dir:
            return None
        path = self._cache_dir / key
        if not path.exists():
            return None
        try:
            data: dict[str, Any] = json.loads(path.read_text())
            return data
        except (json.JSONDecodeError, OSError):
            return None

    def _save_cache(self, key: str, data: dict[str, Any]) -> None:
        if not self._cache_dir:
            return
        path = self._cache_dir / key
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
