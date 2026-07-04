"""High-level Wiki RAG service: collection, indexing, and retrieval."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from qdrant_client import QdrantClient

from mc_pilot.rag.chunker import build_chunks
from mc_pilot.rag.client import WikiClient
from mc_pilot.rag.embedder import CHUNKER_VERSION, Embedder
from mc_pilot.rag.indexer import WikiIndexer
from mc_pilot.rag.models import (
    AnswerResponse,
    IndexMetadata,
    RetrievalResult,
    WikiChunk,
    WikiPage,
)
from mc_pilot.rag.retriever import WikiRetriever

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Category:方块",
    "Category:物品",
    "Category:生物",
    "Category:群系",
    "Category:游戏规则",
    "Category:附魔",
    "Category:状态效果",
    "Category:结构",
    "Category:命令",
)


class WikiService:
    """Orchestrates Wiki acquisition, embedding, indexing, and retrieval."""

    _qdrant_url: str
    _api_url: str
    _cache_dir: Path
    _categories: tuple[str, ...]
    _model_id: str
    _version_range: str

    def __init__(
        self,
        *,
        qdrant_url: str = "http://localhost:6333",
        api_url: str = "https://zh.minecraft.wiki/api.php",
        cache_dir: Path | None = None,
        categories: tuple[str, ...] = DEFAULT_CATEGORIES,
        model_id: str = "BAAI/bge-small-zh-v1.5",
        version_range: str = "26.x",
    ) -> None:
        self._qdrant_url = qdrant_url
        self._api_url = api_url
        self._cache_dir = cache_dir or Path("data/wiki/cache")
        self._categories = categories
        self._model_id = model_id
        self._version_range = version_range

    async def build_index(self) -> IndexMetadata:
        """Full pipeline: fetch Wiki pages, chunk, embed, index, and swap."""
        client = WikiClient(
            api_url=self._api_url,
            cache_dir=self._cache_dir / "api",
        )

        try:
            pages = await self._collect_all_pages(client)
        finally:
            await client.close()

        logger.info("Collected Wiki pages", extra={"count": len(pages)})
        chunks = self._chunk_pages(pages)
        logger.info("Chunked Wiki pages", extra={"chunks": len(chunks)})

        embedder = Embedder(model_id=self._model_id)
        try:
            qdrant = QdrantClient(url=self._qdrant_url)
            indexer = WikiIndexer(client=qdrant, embedder=embedder)
            indexer.ensure_staging()
            indexer.index_chunks(chunks)

            metadata = IndexMetadata(
                embedding_model_id=self._model_id,
                embedding_dimension=embedder.dimension,
                chunker_version=CHUNKER_VERSION,
                built_at=datetime.now(UTC),
                page_count=len(pages),
                chunk_count=len(chunks),
                wiki_categories=self._categories,
            )
            indexer.swap_to_live(metadata)
            return metadata
        finally:
            qdrant.close()

    def get_retriever(self) -> WikiRetriever:
        embedder = Embedder(model_id=self._model_id)
        qdrant = QdrantClient(url=self._qdrant_url)
        return WikiRetriever(client=qdrant, embedder=embedder)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 8,
        retriever: WikiRetriever | None = None,
    ) -> AnswerResponse:
        r = retriever or self.get_retriever()
        if not r.collection_exists():
            return AnswerResponse(
                query=query,
                verified_answer="知识库尚未构建, 请先运行 build 命令。",
                insufficient_evidence=True,
            )

        results = r.retrieve(query, top_k=top_k)
        if not results:
            return AnswerResponse(
                query=query,
                verified_answer="知识库未找到足够依据。",
                insufficient_evidence=True,
            )

        chunks = [hit.text for hit in results]
        context = "\n\n---\n\n".join(chunks)
        verified = _format_sources(context, results)

        return AnswerResponse(
            query=query,
            verified_answer=verified,
            sources=tuple(results),
            insufficient_evidence=False,
        )

    async def _collect_all_pages(self, client: WikiClient) -> list[WikiPage]:
        pages: list[WikiPage] = []
        seen_ids: set[int] = set()

        for category in self._categories:
            logger.info("Collecting category", extra={"category": category})
            member_ids: list[int] = []

            continue_token: str | None = None
            while True:
                data = await client.category_members(
                    category, continue_token=continue_token
                )
                members = (
                    data.get("query", {}).get("categorymembers", [])
                )
                for member in members:
                    pid = member["pageid"]
                    if pid not in seen_ids:
                        member_ids.append(pid)
                        seen_ids.add(pid)

                if "continue" not in data:
                    break
                continue_token = data["continue"]["cmcontinue"]
                await asyncio.sleep(1.0)

            if not member_ids:
                continue

            for batch_start in range(0, len(member_ids), 50):
                batch = member_ids[batch_start : batch_start + 50]
                content_data = await client.page_content(batch)
                pages_data = (
                    content_data.get("query", {}).get("pages", {})
                )
                for _pid_str, page_data in pages_data.items():
                    pid = page_data.get("pageid", 0)
                    if pid < 0:
                        continue
                    title = page_data.get("title", "")
                    if self._should_exclude(title):
                        continue

                    revisions = page_data.get("revisions", [])
                    if not revisions:
                        continue

                    rev = revisions[0]
                    text = rev.get("slots", {}).get("main", {}).get("*", "")
                    page_url = page_data.get("fullurl", "")

                    pages.append(
                        WikiPage(
                            page_id=pid,
                            revision_id=rev.get("revid", 0),
                            title=title,
                            category=category,
                            url=page_url,
                            text=text,
                            fetched_at=datetime.now(UTC),
                            version_range=self._version_range,
                        )
                    )

                await asyncio.sleep(0.5)

        return pages

    def _should_exclude(self, title: str) -> bool:
        exclude_keywords = (
            "基岩版",
            "教育版",
            "原主机版",
            "New Nintendo 3DS",
            "树莓派版",
            "已移除",
            "计划中",
            "版本记录",
            "开发版",
            "快照",
        )
        return any(kw in title for kw in exclude_keywords)

    def index_stats(self) -> dict[str, object]:
        """Return Wiki RAG index statistics from Qdrant."""
        try:
            qdrant = QdrantClient(url=self._qdrant_url)
            info = qdrant.get_collection("mc_wiki_live")
            qdrant.close()
            return {
                "available": True,
                "index_exists": True,
                "chunk_count": info.points_count or 0,
                "vectors_count": info.vectors_count or 0,
            }
        except Exception as exc:
            logger.warning("Failed to get Wiki index stats", extra={"error": str(exc)})
            return {"available": True, "index_exists": False, "error": str(exc)}

    def _chunk_pages(self, pages: list[WikiPage]) -> list[WikiChunk]:
        all_chunks: list[WikiChunk] = []
        for page in pages:
            chunks = build_chunks(
                page_id=page.page_id,
                revision_id=page.revision_id,
                title=page.title,
                category=page.category,
                url=page.url,
                raw_text=page.text,
                version_range=page.version_range,
            )
            all_chunks.extend(chunks)
        return all_chunks


def _format_sources(context: str, results: list[RetrievalResult]) -> str:
    parts: list[str] = []
    for result in results:
        parts.append(f"【{result.title}】(来源: {result.url})")
    source_str = "\n".join(parts)
    return f"{context}\n\n---\n**参考来源**\n{source_str}"
