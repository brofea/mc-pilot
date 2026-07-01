"""Qdrant indexer: staging collection, atomic switch, and payload management."""

from __future__ import annotations

import logging
from typing import TypeGuard

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from mc_pilot.rag.embedder import Embedder
from mc_pilot.rag.models import IndexMetadata, WikiChunk

logger = logging.getLogger(__name__)

COLLECTION_BASE = "mc_wiki"
VECTOR_SIZE = 512
BATCH_SIZE = 100


def _is_dense_vector(value: object) -> TypeGuard[list[int | float]]:
    return isinstance(value, list) and all(
        isinstance(element, int | float) for element in value
    )


class WikiIndexer:
    """Owns Qdrant collection creation, staging swaps, and chunk ingestion."""

    _client: QdrantClient
    _embedder: Embedder

    def __init__(self, client: QdrantClient, embedder: Embedder) -> None:
        self._client = client
        self._embedder = embedder

    @property
    def dimension(self) -> int:
        return self._embedder.dimension

    def collection_name(self, stage: str = "live") -> str:
        return f"{COLLECTION_BASE}_{stage}"

    def ensure_staging(self) -> None:
        """Create or recreate the staging collection."""
        staging = self.collection_name("staging")
        self._client.delete_collection(staging)
        self._client.create_collection(
            collection_name=staging,
            vectors_config=VectorParams(
                size=self._embedder.dimension,
                distance=Distance.COSINE,
            ),
        )
        self._client.create_payload_index(
            collection_name=staging,
            field_name="title",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=staging,
            field_name="category",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=staging,
            field_name="page_id",
            field_schema=PayloadSchemaType.INTEGER,
        )
        logger.info("Staging collection created", extra={"name": staging})

    def index_chunks(self, chunks: list[WikiChunk]) -> int:
        """Embed and upsert chunks into the staging collection in batches."""
        staging = self.collection_name("staging")
        indexed = 0

        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[batch_start : batch_start + BATCH_SIZE]
            texts = [chunk.text for chunk in batch]
            vectors = self._embedder.encode(texts)

            points: list[PointStruct] = []
            for chunk, vector in zip(batch, vectors, strict=True):
                points.append(
                    PointStruct(
                        id=chunk.chunk_id,
                        vector=vector,
                        payload={
                            "page_id": chunk.page_id,
                            "revision_id": chunk.revision_id,
                            "title": chunk.title,
                            "category": chunk.category,
                            "url": chunk.url,
                            "chunk_index": chunk.chunk_index,
                            "text": chunk.text,
                            "version_range": chunk.version_range or "",
                        },
                    )
                )
            self._client.upsert(collection_name=staging, points=points)
            indexed += len(batch)

        logger.info(
            "Chunks indexed into staging",
            extra={"chunks": indexed, "collection": staging},
        )
        return indexed

    def swap_to_live(self, metadata: IndexMetadata) -> None:
        """Migrate staging points to the live collection and drop staging."""
        staging = self.collection_name("staging")
        live = self.collection_name("live")

        self._client.delete_collection(live)
        self._client.create_collection(
            collection_name=live,
            vectors_config=VectorParams(
                size=self._embedder.dimension,
                distance=Distance.COSINE,
            ),
        )
        self._client.create_payload_index(
            collection_name=live,
            field_name="title",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=live,
            field_name="category",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=live,
            field_name="page_id",
            field_schema=PayloadSchemaType.INTEGER,
        )

        points: list[PointStruct] = []
        offset: str | int | None = None
        while True:
            records, offset = self._client.scroll(
                collection_name=staging,
                with_vectors=True,
                offset=offset,
                limit=10_000,
            )
            if not records:
                break
            for rec in records:
                raw_vector = rec.vector
                if _is_dense_vector(raw_vector):
                    vec = [float(value) for value in raw_vector]
                else:
                    vec = [0.0] * self._embedder.dimension
                points.append(
                    PointStruct(
                        id=rec.id,
                        vector=vec,
                        payload=rec.payload,
                    )
                )

        batch_size = 500
        for i in range(0, len(points), batch_size):
            self._client.upsert(
                collection_name=live,
                points=points[i : i + batch_size],
            )

        metadata_payload = metadata.model_dump(mode="json")
        self._client.upsert(
            collection_name=live,
            points=[
                PointStruct(
                    id="__index_metadata__",
                    vector=[0.0] * self._embedder.dimension,
                    payload=metadata_payload,
                )
            ],
        )

        self._client.delete_collection(staging)
        logger.info(
            "Live collection swapped",
            extra={
                "live": live,
                "pages": metadata.page_count,
                "chunks": metadata.chunk_count,
            },
        )

    def get_metadata(self) -> IndexMetadata | None:
        """Retrieve metadata from the live collection."""
        live = self.collection_name("live")
        try:
            points = self._client.retrieve(
                collection_name=live,
                ids=["__index_metadata__"],
                with_payload=True,
            )
        except Exception:
            return None
        if not points:
            return None
        payload = points[0].payload
        if not payload:
            return None
        return IndexMetadata(**payload)
