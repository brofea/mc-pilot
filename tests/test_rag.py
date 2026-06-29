"""Wiki RAG module tests."""

from __future__ import annotations

from datetime import datetime

from mc_pilot.rag.chunker import chunk_by_sections, clean_wiki_text
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
