"""Wiki RAG retriever: dense vector search + title/alias exact boost."""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchText,
    ScoredPoint,
)

from mc_pilot.rag.embedder import Embedder
from mc_pilot.rag.models import RetrievalResult

logger = logging.getLogger(__name__)

TOP_K = 5


class WikiRetriever:
    """Dense retrieval with title/alias exact-boost fallback."""

    _client: QdrantClient
    _embedder: Embedder
    _collection_name: str

    def __init__(
        self,
        client: QdrantClient,
        embedder: Embedder,
        collection_name: str = "mc_wiki_live",
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection_name = collection_name

    def retrieve(self, query: str, *, top_k: int = TOP_K) -> list[RetrievalResult]:
        """Retrieve chunks using dense search with title boost."""
        query_vector = self._embedder.encode_single(query)
        dense_hits = self._search_dense(query_vector, top_k)

        title_hits = self._search_title(query, max(2, top_k // 2))

        merged = self._merge_results(dense_hits, title_hits, top_k)
        return merged

    def collection_exists(self) -> bool:
        try:
            collections = self._client.get_collections()
            names = [c.name for c in collections.collections]
            return self._collection_name in names
        except Exception:
            return False

    def _search_dense(self, vector: list[float], limit: int) -> list[ScoredPoint]:
        try:
            results = self._client.search(
                collection_name=self._collection_name,
                query_vector=vector,
                limit=limit,
                with_payload=True,
                score_threshold=0.3,
            )
            return results
        except Exception:
            return []

    def _search_title(self, query: str, limit: int) -> list[ScoredPoint]:
        try:
            results = self._client.search(
                collection_name=self._collection_name,
                query_vector=[0.0] * self._embedder.dimension,
                query_filter=Filter(
                    must=[FieldCondition(key="title", match=MatchText(text=query))]
                ),
                limit=limit,
                with_payload=True,
                score_threshold=0.0,
            )
            return results
        except Exception:
            return []

    def _merge_results(
        self,
        dense: list[ScoredPoint],
        title: list[ScoredPoint],
        top_k: int,
    ) -> list[RetrievalResult]:
        seen: set[str] = set()
        results: list[RetrievalResult] = []

        # Title hits first (exact boost)
        for pt in title:
            if pt.payload is None:
                continue
            chunk_id = str(pt.id)
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            results.append(self._point_to_result(pt, "title_exact"))

        # Then dense hits
        for pt in dense:
            if pt.payload is None:
                continue
            chunk_id = str(pt.id)
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            results.append(self._point_to_result(pt, "dense"))

        return results[:top_k]

    @staticmethod
    def _point_to_result(pt: ScoredPoint, match_type: str) -> RetrievalResult:
        payload = pt.payload or {}
        return RetrievalResult(
            chunk_id=payload.get("chunk_id", str(pt.id)),
            title=payload.get("title", ""),
            url=payload.get("url", ""),
            revision_id=payload.get("revision_id", 0),
            score=pt.score,
            text=payload.get("text", ""),
            category=payload.get("category", ""),
            match_type=match_type,
        )
