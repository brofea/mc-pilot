"""Wiki RAG module tests."""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

import pytest

from mc_pilot.rag.chunker import chunk_by_sections, clean_wiki_text
from mc_pilot.rag.indexer import METADATA_POINT_ID, WikiIndexer
from mc_pilot.rag.models import (
    AnswerResponse,
    IndexMetadata,
    RetrievalResult,
    WikiChunk,
    WikiPage,
)

# ── Chunker tests ──────────────────────────────────────────────────────


def test_clean_wiki_text_removes_markup() -> None:
    text = "'''粗体''' [[链接|显示文字]] <ref>注释</ref> {{模板}}"
    result = clean_wiki_text(text)
    assert "粗体" in result
    assert "显示文字" in result
    assert "链接" not in result
    assert "ref" not in result
    # <ref> tags removed, but inner text stays
    assert "注释" in result
    assert "模板" not in result


def test_clean_wiki_text_strips_html_entities() -> None:
    text = "方块&amp;物品 &amp;"
    result = clean_wiki_text(text)
    assert "&amp;" not in result


def test_clean_wiki_text_preserves_useful_content() -> None:
    text = "== 概述 ==\n这是 Minecraft 的一个方块。"
    result = clean_wiki_text(text)
    assert "概述" in result
    assert "Minecraft" in result


def test_chunk_by_sections_splits_long_text() -> None:
    long_paragraph = "这是测试 " * 100
    text = f"== 第一节 ==\n{long_paragraph}\n== 第二节 ==\n{long_paragraph}"
    chunks = chunk_by_sections("测试页面", text, max_chunk_chars=200)
    # Each 500-char paragraph produces multiple chunks per section
    assert len(chunks) >= 4


def test_chunk_by_sections_handles_empty_text() -> None:
    chunks = chunk_by_sections("空页面", "")
    assert len(chunks) == 0


def test_chunk_by_sections_handles_no_sections() -> None:
    text = "没有标题的纯文本内容。"
    chunks = chunk_by_sections("无标题页", text)
    assert len(chunks) == 1
    assert chunks[0]["text"] == "没有标题的纯文本内容。"


# ── Model tests ────────────────────────────────────────────────────────


def test_wiki_page_model() -> None:
    page = WikiPage(
        page_id=1,
        revision_id=2,
        title="石头",
        category="Category:方块",
        url="https://zh.minecraft.wiki/石头",
        text="石头是主世界最常见的方块。",
        fetched_at=datetime.now(),
        version_range="26.x",
    )
    assert page.page_id == 1
    assert page.title == "石头"


def test_wiki_chunk_model() -> None:
    chunk = WikiChunk(
        chunk_id="1_0",
        page_id=1,
        revision_id=2,
        title="石头",
        category="Category:方块",
        url="https://zh.minecraft.wiki/石头",
        text="石头是主世界最常见的方块。",
        chunk_index=0,
        total_chunks=1,
        version_range="26.x",
        english_title="Stone",
        resource_id="minecraft:stone",
    )
    assert chunk.chunk_id == "1_0"
    assert chunk.english_title == "Stone"


def test_retrieval_result_model() -> None:
    result = RetrievalResult(
        chunk_id="1_0",
        title="石头",
        url="https://zh.minecraft.wiki/石头",
        revision_id=2,
        score=0.95,
        text="石头是主世界最常见的方块。",
        category="Category:方块",
        match_type="dense",
    )
    assert result.score == 0.95
    assert result.match_type == "dense"


def test_answer_response_with_sources() -> None:
    sources = (
        RetrievalResult(
            chunk_id="1_0",
            title="石头",
            url="https://zh.minecraft.wiki/石头",
            revision_id=2,
            score=0.95,
            text="石头是主世界最常见的方块。",
            category="Category:方块",
            match_type="dense",
        ),
    )
    answer = AnswerResponse(
        query="什么是石头",
        verified_answer="石头是主世界最常见的方块。",
        sources=sources,
        insufficient_evidence=False,
    )
    assert answer.verified_answer
    assert len(answer.sources) == 1
    assert not answer.insufficient_evidence


def test_answer_response_insufficient_evidence() -> None:
    answer = AnswerResponse(
        query="不存在的物品",
        verified_answer="知识库未找到足够依据。",
        insufficient_evidence=True,
    )
    assert answer.insufficient_evidence
    assert answer.unverified_supplement is None


def test_index_metadata_model() -> None:
    metadata = IndexMetadata(
        embedding_model_id="BAAI/bge-small-zh-v1.5",
        embedding_dimension=512,
        chunker_version="1.0.0",
        built_at=datetime.now(),
        page_count=100,
        chunk_count=500,
        wiki_categories=("Category:方块", "Category:物品"),
    )
    assert metadata.embedding_dimension == 512
    assert metadata.page_count == 100


def test_ensure_staging_uses_non_reserved_log_field(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = Mock()
    embedder = Mock()
    embedder.dimension = 512
    indexer = WikiIndexer(client=client, embedder=embedder)

    with caplog.at_level(logging.INFO):
        indexer.ensure_staging()

    record = next(
        record
        for record in caplog.records
        if record.message == "Staging collection created"
    )
    assert record.__dict__["collection_name"] == "mc_wiki_staging"


def test_index_chunks_maps_domain_id_to_qdrant_uuid() -> None:
    client = Mock()
    embedder = Mock()
    embedder.dimension = 512
    embedder.encode.return_value = [[0.0] * 512]
    indexer = WikiIndexer(client=client, embedder=embedder)
    chunk = WikiChunk(
        chunk_id="478_0",
        page_id=478,
        revision_id=2,
        title="石头",
        category="Category:方块",
        url="https://zh.minecraft.wiki/石头",
        text="石头是方块。",
        chunk_index=0,
        total_chunks=1,
    )

    assert indexer.index_chunks([chunk]) == 1
    points = client.upsert.call_args.kwargs["points"]
    assert str(UUID(str(points[0].id))) == points[0].id
    assert points[0].payload["chunk_id"] == "478_0"
    assert str(UUID(METADATA_POINT_ID)) == METADATA_POINT_ID


def test_swap_to_live_stops_when_last_scroll_page_has_no_offset() -> None:
    client = Mock()
    embedder = Mock()
    embedder.dimension = 512
    record = Mock()
    record.id = "f7e5851f-2925-5c86-a6eb-dfc28ee11e02"
    record.vector = [0.0] * 512
    record.payload = {"chunk_id": "478_0"}
    client.scroll.return_value = ([record], None)
    indexer = WikiIndexer(client=client, embedder=embedder)
    metadata = IndexMetadata(
        embedding_model_id="BAAI/bge-small-zh-v1.5",
        embedding_dimension=512,
        chunker_version="1.0.0",
        built_at=datetime.now(),
        page_count=1,
        chunk_count=1,
    )

    indexer.swap_to_live(metadata)

    client.scroll.assert_called_once()
    assert client.upsert.call_count == 2
