"""Wiki content cleaner and section-aware chunker."""

from __future__ import annotations

import logging
import re

from mc_pilot.rag.models import WikiChunk

logger = logging.getLogger(__name__)

_SECTION_RE = re.compile(r"^(=+)\s*(.+?)\s*\1$", re.MULTILINE)
_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;")
_WIKILINK_RE = re.compile(r"\[\[:?(?:[^|\]]+\|)?([^\]]+)\]\]")


def clean_wiki_text(text: str) -> str:
    """Remove Wiki markup and HTML noise, keep plain readable text."""
    text = _HTML_ENTITY_RE.sub(" ", text)
    text = _WIKILINK_RE.sub(r"\1", text)
    text = re.sub(r"'{2,}", "", text)
    text = re.sub(r"\{\{[^{}]*?\}\}", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[https?://[^\]\s]+(?:\s+[^\]]+)?\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def chunk_by_sections(
    title: str,
    text: str,
    *,
    max_chunk_chars: int = 600,
    overlap_chars: int = 50,
) -> list[dict[str, object]]:
    """Split cleaned Wiki text into overlapping content chunks by section."""
    if not text.strip():
        return []

    # If no section headers, chunk entire text
    if not _SECTION_RE.search(text):
        return _chunk_paragraphs(text, title, max_chunk_chars, overlap_chars)

    parts = _SECTION_RE.split(text)
    # parts: [before_first_section, level1, title1, body1, level2, title2, body2, ...]
    chunks: list[dict[str, object]] = []

    # Add pre-section text if present
    if parts[0].strip():
        chunks.extend(
            _chunk_paragraphs(parts[0], title, max_chunk_chars, overlap_chars)
        )

    for i in range(1, len(parts) - 2, 3):
        section_title = parts[i + 1].strip()
        body = parts[i + 2].strip() if i + 2 < len(parts) else ""
        if body:
            chunks.extend(
                _chunk_paragraphs(body, section_title, max_chunk_chars, overlap_chars)
            )

    return chunks


def _chunk_paragraphs(
    text: str,
    section_title: str,
    max_chunk_chars: int,
    overlap_chars: int,
) -> list[dict[str, object]]:
    lines = [p.strip() for p in text.split("\n") if p.strip()]
    if not lines:
        return []

    paragraphs: list[str] = []
    for line in lines:
        if len(line) > max_chunk_chars:
            # Force-split long monolithic lines
            for idx in range(0, len(line), max_chunk_chars - overlap_chars):
                paragraphs.append(line[idx : idx + max_chunk_chars])
        else:
            paragraphs.append(line)

    chunks: list[dict[str, object]] = []
    current_chunk: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > max_chunk_chars and current_chunk:
            chunks.append(
                {"section": section_title, "text": "\n".join(current_chunk)}
            )
            overlap_text = (
                current_chunk[-1][:overlap_chars] if current_chunk else ""
            )
            current_chunk = [overlap_text] if overlap_text else []
            current_len = len(overlap_text)
        current_chunk.append(para)
        current_len += len(para)

    if current_chunk:
        chunks.append({"section": section_title, "text": "\n".join(current_chunk)})

    return chunks


def build_chunks(
    page_id: int,
    revision_id: int,
    title: str,
    category: str,
    url: str,
    raw_text: str,
    *,
    version_range: str | None = None,
) -> list[WikiChunk]:
    cleaned = clean_wiki_text(raw_text)
    if not cleaned or not cleaned.strip():
        return []

    raw_chunks = chunk_by_sections(title, cleaned)
    total = len(raw_chunks)
    result: list[WikiChunk] = []
    for idx, rc in enumerate(raw_chunks):
        section_text = str(rc.get("text", ""))
        if not section_text.strip():
            continue
        chunk_id = f"{page_id}_{idx}"
        result.append(
            WikiChunk(
                chunk_id=chunk_id,
                page_id=page_id,
                revision_id=revision_id,
                title=title,
                category=category,
                url=url,
                text=section_text,
                chunk_index=idx,
                total_chunks=total,
                version_range=version_range,
                english_title=None,
                resource_id=None,
            )
        )
    return result
