"""Data models for RAG preparation artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from finevent.types import JsonDict


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    article_id: str
    chunk_level: str
    chunk_index: int
    text: str
    title: str | None
    source: str
    url: str
    published_at: str | None
    content_hash: str
    chunk_hash: str
    text_word_count: int
    tickers_hint: list[str]
    company_names_hint: list[str]
    sector_hints: list[str]
    event_keywords: list[str]
    event_type_hints: list[str]
    event_subtype_hints: list[str]
    parent_chunk_id: str | None = None
    paragraph_start: int | None = None
    paragraph_end: int | None = None
    metadata: JsonDict = field(default_factory=dict)
    version: str = "m03_v1"

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class EmbeddingRecord:
    embedding_id: str
    chunk_id: str
    article_id: str
    embedding_model: str
    embedding_dimension: int
    content_hash: str
    chunk_hash: str
    vector: list[float]
    status: str
    created_at: str
    cache_hit: bool = False
    error: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)
