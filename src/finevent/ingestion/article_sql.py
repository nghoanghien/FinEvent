"""PostgreSQL sync helpers for cleaned article records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from finevent.jsonl import read_jsonl
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class ArticleSyncResult:
    article_count: int
    metadata_count: int


def sync_clean_articles_jsonl(
    engine: Any,
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
) -> ArticleSyncResult:
    articles = read_jsonl(articles_path)
    sql = _sqlalchemy_text()

    with engine.begin() as connection:
        for article in articles:
            _upsert_article(connection, sql, article)
            _upsert_article_metadata(connection, sql, article)

    return ArticleSyncResult(article_count=len(articles), metadata_count=len(articles))


def _upsert_article(connection: Any, sql: Any, article: JsonDict) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO articles (
                article_id,
                source,
                url,
                title,
                published_at,
                author,
                clean_text_path,
                content_hash,
                language
            )
            VALUES (
                :article_id,
                :source,
                :url,
                :title,
                CAST(:published_at AS TIMESTAMPTZ),
                :author,
                :clean_text_path,
                :content_hash,
                :language
            )
            ON CONFLICT (article_id)
            DO UPDATE SET
                source = EXCLUDED.source,
                url = EXCLUDED.url,
                title = EXCLUDED.title,
                published_at = EXCLUDED.published_at,
                author = EXCLUDED.author,
                clean_text_path = EXCLUDED.clean_text_path,
                content_hash = EXCLUDED.content_hash,
                language = EXCLUDED.language
            """
        ),
        {
            "article_id": article["article_id"],
            "source": article.get("source") or "unknown",
            "url": article.get("url") or "",
            "title": article.get("title"),
            "published_at": article.get("published_at"),
            "author": article.get("author"),
            "clean_text_path": article.get("clean_text_path"),
            "content_hash": article.get("content_hash"),
            "language": article.get("language") or "vi",
        },
    )


def _upsert_article_metadata(connection: Any, sql: Any, article: JsonDict) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO article_metadata (
                article_id,
                tickers_hint,
                company_names_hint,
                sector_hints,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
                metadata_confidence,
                parse_warnings
            )
            VALUES (
                :article_id,
                CAST(:tickers_hint AS JSONB),
                CAST(:company_names_hint AS JSONB),
                CAST(:sector_hints AS JSONB),
                CAST(:event_keywords AS JSONB),
                CAST(:event_type_hints AS JSONB),
                CAST(:event_subtype_hints AS JSONB),
                :metadata_confidence,
                CAST(:parse_warnings AS JSONB)
            )
            ON CONFLICT (article_id)
            DO UPDATE SET
                tickers_hint = EXCLUDED.tickers_hint,
                company_names_hint = EXCLUDED.company_names_hint,
                sector_hints = EXCLUDED.sector_hints,
                event_keywords = EXCLUDED.event_keywords,
                event_type_hints = EXCLUDED.event_type_hints,
                event_subtype_hints = EXCLUDED.event_subtype_hints,
                metadata_confidence = EXCLUDED.metadata_confidence,
                parse_warnings = EXCLUDED.parse_warnings
            """
        ),
        {
            "article_id": article["article_id"],
            "tickers_hint": _json(article.get("tickers_hint", [])),
            "company_names_hint": _json(article.get("company_names_hint", [])),
            "sector_hints": _json(article.get("sector_hints", [])),
            "event_keywords": _json(article.get("event_keywords", [])),
            "event_type_hints": _json(article.get("event_type_hints", [])),
            "event_subtype_hints": _json(article.get("event_subtype_hints", [])),
            "metadata_confidence": article.get("metadata_confidence"),
            "parse_warnings": _json(article.get("parse_warnings", [])),
        },
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for article sync.") from exc
    return text
