"""Data models for ingestion artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from finevent.types import JsonDict


@dataclass(frozen=True)
class ParsedArticle:
    source: str
    url: str
    title: str | None
    published_at: str | None
    body_text: str
    author: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RawArticleRecord:
    article_id: str
    source: str
    url: str
    title: str | None
    published_at: str | None
    author: str | None
    http_status: int | None
    crawl_time: str
    html_path: str
    raw_text: str
    parse_status: str
    parse_warnings: list[str]

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class CleanArticleRecord:
    article_id: str
    source: str
    url: str
    title: str | None
    published_at: str | None
    text: str
    tickers_hint: list[str]
    company_names_hint: list[str]
    sector_hints: list[str]
    event_keywords: list[str]
    event_type_hints: list[str]
    event_subtype_hints: list[str]
    language: str
    content_hash: str
    text_char_count: int
    version: str = "v1"

    def to_dict(self) -> JsonDict:
        return asdict(self)
