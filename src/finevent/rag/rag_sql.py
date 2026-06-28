"""PostgreSQL sync helpers for retrieval chunks and embeddings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from finevent.jsonl import read_jsonl
from finevent.rag.pipeline import chunks_from_jsonl
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class RetrievalSyncResult:
    article_count: int
    chunk_count: int
    embedding_count: int
    chunk_pattern_count: int


def sync_retrieval_artifacts(
    engine: Any,
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    chunks_path: PathLike = "data/processed/chunks.jsonl",
    embeddings_path: PathLike = "data/retrieval/chunk_embeddings.jsonl",
    chunk_patterns_path: PathLike = "data/processed/chunk_patterns.jsonl",
) -> RetrievalSyncResult:
    articles = read_jsonl(articles_path)
    chunks = chunks_from_jsonl(chunks_path)
    embeddings = read_jsonl(embeddings_path)
    chunk_patterns = read_jsonl(chunk_patterns_path) if _path_exists(chunk_patterns_path) else []
    articles_by_id = {str(article["article_id"]): article for article in articles}
    chunk_article_ids = {chunk.article_id for chunk in chunks}
    sql = _sqlalchemy_text()

    with engine.begin() as connection:
        for article_id in sorted(chunk_article_ids):
            article = articles_by_id.get(article_id)
            if article is None:
                continue
            _upsert_document(connection, sql, article)
        for chunk in chunks:
            _upsert_chunk(connection, sql, chunk.to_dict())
        for embedding in embeddings:
            if embedding.get("status") == "success":
                _upsert_embedding(connection, sql, embedding)
        _replace_chunk_patterns(connection, sql, chunk_patterns)

    return RetrievalSyncResult(
        article_count=len(chunk_article_ids),
        chunk_count=len(chunks),
        embedding_count=sum(1 for record in embeddings if record.get("status") == "success"),
        chunk_pattern_count=len(chunk_patterns),
    )


def _upsert_document(connection: Any, sql: Any, article: JsonDict) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO financial_news_documents (
                article_id,
                source,
                url,
                title,
                published_at,
                content_hash,
                language,
                tickers_hint,
                company_names_hint,
                sector_hints,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
                updated_at
            )
            VALUES (
                :article_id,
                :source,
                :url,
                :title,
                CAST(:published_at AS TIMESTAMPTZ),
                :content_hash,
                :language,
                CAST(:tickers_hint AS JSONB),
                CAST(:company_names_hint AS JSONB),
                CAST(:sector_hints AS JSONB),
                CAST(:event_keywords AS JSONB),
                CAST(:event_type_hints AS JSONB),
                CAST(:event_subtype_hints AS JSONB),
                NOW()
            )
            ON CONFLICT (article_id)
            DO UPDATE SET
                source = EXCLUDED.source,
                url = EXCLUDED.url,
                title = EXCLUDED.title,
                published_at = EXCLUDED.published_at,
                content_hash = EXCLUDED.content_hash,
                language = EXCLUDED.language,
                tickers_hint = EXCLUDED.tickers_hint,
                company_names_hint = EXCLUDED.company_names_hint,
                sector_hints = EXCLUDED.sector_hints,
                event_keywords = EXCLUDED.event_keywords,
                event_type_hints = EXCLUDED.event_type_hints,
                event_subtype_hints = EXCLUDED.event_subtype_hints,
                updated_at = NOW()
            """
        ),
        {
            "article_id": article["article_id"],
            "source": article.get("source") or "unknown",
            "url": article.get("url") or "",
            "title": article.get("title"),
            "published_at": article.get("published_at"),
            "content_hash": article.get("content_hash"),
            "language": article.get("language") or "vi",
            "tickers_hint": _json(article.get("tickers_hint", [])),
            "company_names_hint": _json(article.get("company_names_hint", [])),
            "sector_hints": _json(article.get("sector_hints", [])),
            "event_keywords": _json(article.get("event_keywords", [])),
            "event_type_hints": _json(article.get("event_type_hints", [])),
            "event_subtype_hints": _json(article.get("event_subtype_hints", [])),
        },
    )


def _upsert_chunk(connection: Any, sql: Any, chunk: JsonDict) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO financial_news_chunks (
                chunk_id,
                article_id,
                chunk_level,
                chunk_index,
                parent_chunk_id,
                text,
                title,
                source,
                url,
                published_at,
                content_hash,
                chunk_hash,
                text_word_count,
                tickers_hint,
                company_names_hint,
                sector_hints,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
                pattern_refs,
                paragraph_start,
                paragraph_end,
                metadata,
                version,
                updated_at
            )
            VALUES (
                :chunk_id,
                :article_id,
                :chunk_level,
                :chunk_index,
                :parent_chunk_id,
                :text,
                :title,
                :source,
                :url,
                CAST(:published_at AS TIMESTAMPTZ),
                :content_hash,
                :chunk_hash,
                :text_word_count,
                CAST(:tickers_hint AS JSONB),
                CAST(:company_names_hint AS JSONB),
                CAST(:sector_hints AS JSONB),
                CAST(:event_keywords AS JSONB),
                CAST(:event_type_hints AS JSONB),
                CAST(:event_subtype_hints AS JSONB),
                CAST(:pattern_refs AS JSONB),
                :paragraph_start,
                :paragraph_end,
                CAST(:metadata AS JSONB),
                :version,
                NOW()
            )
            ON CONFLICT (chunk_id)
            DO UPDATE SET
                text = EXCLUDED.text,
                title = EXCLUDED.title,
                source = EXCLUDED.source,
                url = EXCLUDED.url,
                published_at = EXCLUDED.published_at,
                content_hash = EXCLUDED.content_hash,
                chunk_hash = EXCLUDED.chunk_hash,
                text_word_count = EXCLUDED.text_word_count,
                tickers_hint = EXCLUDED.tickers_hint,
                company_names_hint = EXCLUDED.company_names_hint,
                sector_hints = EXCLUDED.sector_hints,
                event_keywords = EXCLUDED.event_keywords,
                event_type_hints = EXCLUDED.event_type_hints,
                event_subtype_hints = EXCLUDED.event_subtype_hints,
                pattern_refs = EXCLUDED.pattern_refs,
                paragraph_start = EXCLUDED.paragraph_start,
                paragraph_end = EXCLUDED.paragraph_end,
                metadata = EXCLUDED.metadata,
                version = EXCLUDED.version,
                updated_at = NOW()
            """
        ),
        {
            "chunk_id": chunk["chunk_id"],
            "article_id": chunk["article_id"],
            "chunk_level": chunk["chunk_level"],
            "chunk_index": chunk["chunk_index"],
            "parent_chunk_id": chunk.get("parent_chunk_id"),
            "text": chunk["text"],
            "title": chunk.get("title"),
            "source": chunk.get("source") or "unknown",
            "url": chunk.get("url") or "",
            "published_at": chunk.get("published_at"),
            "content_hash": chunk.get("content_hash"),
            "chunk_hash": chunk["chunk_hash"],
            "text_word_count": chunk["text_word_count"],
            "tickers_hint": _json(chunk.get("tickers_hint", [])),
            "company_names_hint": _json(chunk.get("company_names_hint", [])),
            "sector_hints": _json(chunk.get("sector_hints", [])),
            "event_keywords": _json(chunk.get("event_keywords", [])),
            "event_type_hints": _json(chunk.get("event_type_hints", [])),
            "event_subtype_hints": _json(chunk.get("event_subtype_hints", [])),
            "pattern_refs": _json(chunk.get("pattern_refs", [])),
            "paragraph_start": chunk.get("paragraph_start"),
            "paragraph_end": chunk.get("paragraph_end"),
            "metadata": _json(chunk.get("metadata", {})),
            "version": chunk.get("version") or "m03_v1",
        },
    )


def _upsert_embedding(connection: Any, sql: Any, embedding: JsonDict) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO financial_news_chunk_embeddings (
                embedding_id,
                chunk_id,
                article_id,
                embedding_model,
                embedding_dimension,
                content_hash,
                chunk_hash,
                embedding,
                status,
                error
            )
            VALUES (
                :embedding_id,
                :chunk_id,
                :article_id,
                :embedding_model,
                :embedding_dimension,
                :content_hash,
                :chunk_hash,
                CAST(:embedding AS vector),
                :status,
                :error
            )
            ON CONFLICT (chunk_id, embedding_model)
            DO UPDATE SET
                embedding_id = EXCLUDED.embedding_id,
                article_id = EXCLUDED.article_id,
                embedding_dimension = EXCLUDED.embedding_dimension,
                content_hash = EXCLUDED.content_hash,
                chunk_hash = EXCLUDED.chunk_hash,
                embedding = EXCLUDED.embedding,
                status = EXCLUDED.status,
                error = EXCLUDED.error
            """
        ),
        {
            "embedding_id": embedding["embedding_id"],
            "chunk_id": embedding["chunk_id"],
            "article_id": embedding["article_id"],
            "embedding_model": embedding["embedding_model"],
            "embedding_dimension": embedding["embedding_dimension"],
            "content_hash": embedding.get("content_hash"),
            "chunk_hash": embedding["chunk_hash"],
            "embedding": _pgvector_literal(embedding.get("vector", [])),
            "status": embedding.get("status") or "success",
            "error": embedding.get("error"),
        },
    )


def _replace_chunk_patterns(connection: Any, sql: Any, mappings: list[JsonDict]) -> None:
    connection.execute(sql("DELETE FROM financial_news_chunk_patterns"))
    for mapping in mappings:
        connection.execute(
            sql(
                """
                INSERT INTO financial_news_chunk_patterns (
                    chunk_id,
                    article_id,
                    pattern_id,
                    event_id,
                    event_type,
                    event_subtype,
                    pattern_kind,
                    document_label,
                    match_strategy,
                    match_score,
                    pattern_ref
                )
                VALUES (
                    :chunk_id,
                    :article_id,
                    :pattern_id,
                    :event_id,
                    :event_type,
                    :event_subtype,
                    :pattern_kind,
                    :document_label,
                    :match_strategy,
                    :match_score,
                    CAST(:pattern_ref AS JSONB)
                )
                ON CONFLICT (chunk_id, pattern_id)
                DO UPDATE SET
                    article_id = EXCLUDED.article_id,
                    event_id = EXCLUDED.event_id,
                    event_type = EXCLUDED.event_type,
                    event_subtype = EXCLUDED.event_subtype,
                    pattern_kind = EXCLUDED.pattern_kind,
                    document_label = EXCLUDED.document_label,
                    match_strategy = EXCLUDED.match_strategy,
                    match_score = EXCLUDED.match_score,
                    pattern_ref = EXCLUDED.pattern_ref
                """
            ),
            {
                "chunk_id": mapping["chunk_id"],
                "article_id": mapping["article_id"],
                "pattern_id": mapping["pattern_id"],
                "event_id": mapping.get("event_id"),
                "event_type": mapping.get("event_type"),
                "event_subtype": mapping.get("event_subtype"),
                "pattern_kind": mapping.get("pattern_kind"),
                "document_label": mapping.get("document_label"),
                "match_strategy": mapping.get("match_strategy"),
                "match_score": mapping.get("match_score") or 0.0,
                "pattern_ref": _json(mapping),
            },
        )


def _pgvector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for PostgreSQL retrieval sync.") from exc
    return text


def _path_exists(path: PathLike) -> bool:
    from pathlib import Path

    return Path(path).exists()
