"""Wiki RAG domain models and retrieval response contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, PlainValidator


def _validate_iso_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError(f"Expected ISO-format datetime, got {type(value)}")


def _serialize_iso_datetime(value: datetime) -> str:
    return value.isoformat()


IsoDateTime = Annotated[
    datetime,
    PlainValidator(_validate_iso_datetime),
    PlainSerializer(_serialize_iso_datetime, when_used="json"),
]


class WikiPage(BaseModel):
    """A single Wiki page with metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    page_id: int
    revision_id: int
    title: str
    category: str
    url: str
    text: str
    fetched_at: IsoDateTime
    version_range: str | None = None  # e.g. "26.x"


class WikiChunk(BaseModel):
    """A chunk of Wiki text prepared for embedding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str  # composite: {page_id}_{chunk_index}
    page_id: int
    revision_id: int
    title: str
    category: str
    url: str
    text: str
    chunk_index: int
    total_chunks: int
    version_range: str | None = None
    english_title: str | None = None
    resource_id: str | None = None


class RetrievalResult(BaseModel):
    """A single retrieval hit with metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    title: str
    url: str
    revision_id: int
    score: float
    text: str
    category: str
    match_type: str  # "dense" | "title_exact" | "alias"


class AnswerResponse(BaseModel):
    """Full answer response: verified + unverified supplement + sources."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    verified_answer: str
    unverified_supplement: str | None = None
    sources: tuple[RetrievalResult, ...] = ()
    insufficient_evidence: bool = False
    version_id: str = ""


class IndexMetadata(BaseModel):
    """Metadata persisted alongside the Qdrant collection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    embedding_model_id: str
    embedding_dimension: int
    chunker_version: str
    built_at: IsoDateTime
    page_count: int
    chunk_count: int
    wiki_categories: tuple[str, ...] = ()
