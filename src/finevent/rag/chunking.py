"""Structure-aware chunking for Vietnamese financial news."""

from __future__ import annotations

import re

from finevent.ingestion.text import normalize_text, text_hash
from finevent.rag.models import ChunkRecord
from finevent.types import JsonDict

DOCUMENT_LEVEL = "document"
SECTION_LEVEL = "section"
PARAGRAPH_LEVEL = "paragraph"


def build_article_chunks(
    article: JsonDict,
    *,
    target_words: int = 420,
    max_words: int = 620,
    overlap_words: int = 80,
) -> list[ChunkRecord]:
    text = normalize_text(str(article.get("text") or ""))
    if not text:
        return []

    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []

    chunks: list[ChunkRecord] = []
    document_text = _document_text(article, paragraphs, max_words=max_words)
    document_chunk_id = _chunk_id(article["article_id"], DOCUMENT_LEVEL, 0)
    chunks.append(
        _make_chunk(
            article,
            chunk_id=document_chunk_id,
            chunk_level=DOCUMENT_LEVEL,
            chunk_index=0,
            text=document_text,
            paragraph_start=0,
            paragraph_end=len(paragraphs) - 1,
            parent_chunk_id=None,
            metadata={
                "representation": "title_plus_body_summary",
                "paragraph_count": len(paragraphs),
                "preprocessing": article.get("preprocessing", {}),
            },
        )
    )

    section_groups = _group_paragraphs(
        paragraphs,
        target_words=target_words,
        max_words=max_words,
        overlap_words=overlap_words,
    )
    for section_index, group in enumerate(section_groups):
        section_chunk_id = _chunk_id(article["article_id"], SECTION_LEVEL, section_index)
        section_text = "\n".join(paragraphs[start] for start in group)
        chunks.append(
            _make_chunk(
                article,
                chunk_id=section_chunk_id,
                chunk_level=SECTION_LEVEL,
                chunk_index=section_index,
                text=section_text,
                paragraph_start=group[0],
                paragraph_end=group[-1],
                parent_chunk_id=document_chunk_id,
                metadata={
                    "representation": "paragraph_group",
                    "paragraph_indexes": group,
                    "preprocessing": article.get("preprocessing", {}),
                },
            )
        )

    paragraph_chunk_index = 0
    for paragraph_index, paragraph in enumerate(paragraphs):
        paragraph_slices = _split_long_paragraph(
            paragraph,
            max_words=max_words,
            overlap_words=overlap_words,
        )
        for slice_index, paragraph_text in enumerate(paragraph_slices):
            chunks.append(
                _make_chunk(
                    article,
                    chunk_id=_chunk_id(
                        article["article_id"],
                        PARAGRAPH_LEVEL,
                        paragraph_chunk_index,
                    ),
                    chunk_level=PARAGRAPH_LEVEL,
                    chunk_index=paragraph_chunk_index,
                    text=paragraph_text,
                    paragraph_start=paragraph_index,
                    paragraph_end=paragraph_index,
                    parent_chunk_id=document_chunk_id,
                    metadata={
                        "representation": "evidence_paragraph",
                        "paragraph_index": paragraph_index,
                        "paragraph_slice": slice_index,
                        "preprocessing": article.get("preprocessing", {}),
                    },
                )
            )
            paragraph_chunk_index += 1

    return chunks


def build_corpus_chunks(
    articles: list[JsonDict],
    *,
    target_words: int = 420,
    max_words: int = 620,
    overlap_words: int = 80,
) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for article in articles:
        if not _is_indexable_article(article):
            continue
        chunks.extend(
            build_article_chunks(
                article,
                target_words=target_words,
                max_words=max_words,
                overlap_words=overlap_words,
            )
        )
    return chunks


def _make_chunk(
    article: JsonDict,
    *,
    chunk_id: str,
    chunk_level: str,
    chunk_index: int,
    text: str,
    paragraph_start: int | None,
    paragraph_end: int | None,
    parent_chunk_id: str | None,
    metadata: JsonDict,
) -> ChunkRecord:
    normalized_text = normalize_text(text)
    chunk_hash = text_hash(normalized_text)
    return ChunkRecord(
        chunk_id=chunk_id,
        article_id=str(article["article_id"]),
        chunk_level=chunk_level,
        chunk_index=chunk_index,
        text=normalized_text,
        title=article.get("title"),
        source=str(article.get("source") or "unknown"),
        url=str(article.get("url") or ""),
        published_at=article.get("published_at"),
        content_hash=str(article.get("content_hash") or ""),
        chunk_hash=chunk_hash,
        text_word_count=count_words(normalized_text),
        tickers_hint=list(article.get("tickers_hint", [])),
        company_names_hint=list(article.get("company_names_hint", [])),
        sector_hints=list(article.get("sector_hints", [])),
        event_keywords=list(article.get("event_keywords", [])),
        event_type_hints=list(article.get("event_type_hints", [])),
        event_subtype_hints=list(article.get("event_subtype_hints", [])),
        pattern_refs=[],
        parent_chunk_id=parent_chunk_id,
        paragraph_start=paragraph_start,
        paragraph_end=paragraph_end,
        metadata=metadata,
    )


def _is_indexable_article(article: JsonDict) -> bool:
    return (
        bool(article.get("article_id"))
        and bool(normalize_text(str(article.get("text") or "")))
        and str(article.get("language") or "vi").lower() == "vi"
    )


def _document_text(article: JsonDict, paragraphs: list[str], *, max_words: int) -> str:
    title = normalize_text(str(article.get("title") or ""))
    body = _truncate_words("\n".join(paragraphs), max_words=max_words)
    if title:
        return normalize_text(f"{title}\n{body}")
    return body


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = [normalize_text(part) for part in re.split(r"\n{1,}", normalize_text(text))]
    return [paragraph for paragraph in paragraphs if paragraph]


def _group_paragraphs(
    paragraphs: list[str],
    *,
    target_words: int,
    max_words: int,
    overlap_words: int,
) -> list[list[int]]:
    groups: list[list[int]] = []
    current: list[int] = []
    current_words = 0

    for index, paragraph in enumerate(paragraphs):
        paragraph_words = count_words(paragraph)
        if current and current_words + paragraph_words > max_words:
            groups.append(current)
            current = _overlap_paragraph_indexes(paragraphs, current, overlap_words=overlap_words)
            current_words = sum(count_words(paragraphs[item]) for item in current)

        current.append(index)
        current_words += paragraph_words
        if current_words >= target_words:
            groups.append(current)
            current = _overlap_paragraph_indexes(paragraphs, current, overlap_words=overlap_words)
            current_words = sum(count_words(paragraphs[item]) for item in current)

    if current and (not groups or current != groups[-1]):
        groups.append(current)
    return groups


def _overlap_paragraph_indexes(
    paragraphs: list[str],
    current: list[int],
    *,
    overlap_words: int,
) -> list[int]:
    if overlap_words <= 0:
        return []
    selected: list[int] = []
    word_count = 0
    for index in reversed(current):
        selected.insert(0, index)
        word_count += count_words(paragraphs[index])
        if word_count >= overlap_words:
            break
    return selected


def _split_long_paragraph(paragraph: str, *, max_words: int, overlap_words: int) -> list[str]:
    if count_words(paragraph) <= max_words:
        return [paragraph]

    sentences = _split_sentences(paragraph)
    slices: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        sentence_words = count_words(sentence)
        if current and current_words + sentence_words > max_words:
            slices.append(" ".join(current))
            current = _tail_overlap_sentences(current, overlap_words=overlap_words)
            current_words = count_words(" ".join(current))
        current.append(sentence)
        current_words += sentence_words
    if current:
        slices.append(" ".join(current))
    return slices


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?;:])\s+", text) if part.strip()]


def _tail_overlap_sentences(sentences: list[str], *, overlap_words: int) -> list[str]:
    if overlap_words <= 0:
        return []
    selected: list[str] = []
    word_count = 0
    for sentence in reversed(sentences):
        selected.insert(0, sentence)
        word_count += count_words(sentence)
        if word_count >= overlap_words:
            break
    return selected


def _truncate_words(text: str, *, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def count_words(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _chunk_id(article_id: str, level: str, index: int) -> str:
    return f"{article_id}_{level}_{index:04d}"
