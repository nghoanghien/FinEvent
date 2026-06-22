"""Admin database browser endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.sql.schema import Column, Table

from finevent.api.errors import api_error
from finevent.api.serialization import to_jsonable
from finevent.database import schema
from finevent.db import get_sqlalchemy_engine

router = APIRouter(prefix="/admin/db", tags=["admin-db"])


@dataclass(frozen=True)
class EntityConfig:
    table: Table
    id_column: Column[Any]
    columns: tuple[Column[Any], ...]
    searchable_columns: tuple[Column[Any], ...]
    order_column: Column[Any] | None = None


ENTITY_CONFIGS: dict[str, EntityConfig] = {
    "articles": EntityConfig(
        table=schema.financial_news_documents,
        id_column=schema.financial_news_documents.c.article_id,
        columns=(
            schema.financial_news_documents.c.article_id,
            schema.financial_news_documents.c.source,
            schema.financial_news_documents.c.title,
            schema.financial_news_documents.c.url,
            schema.financial_news_documents.c.published_at,
            schema.financial_news_documents.c.tickers_hint,
            schema.financial_news_documents.c.event_type_hints,
            schema.financial_news_documents.c.created_at,
        ),
        searchable_columns=(
            schema.financial_news_documents.c.article_id,
            schema.financial_news_documents.c.title,
            schema.financial_news_documents.c.url,
            schema.financial_news_documents.c.source,
        ),
        order_column=schema.financial_news_documents.c.created_at,
    ),
    "chunks": EntityConfig(
        table=schema.financial_news_chunks,
        id_column=schema.financial_news_chunks.c.chunk_id,
        columns=(
            schema.financial_news_chunks.c.chunk_id,
            schema.financial_news_chunks.c.article_id,
            schema.financial_news_chunks.c.chunk_level,
            schema.financial_news_chunks.c.chunk_index,
            schema.financial_news_chunks.c.title,
            schema.financial_news_chunks.c.text_word_count,
            schema.financial_news_chunks.c.event_type_hints,
            schema.financial_news_chunks.c.created_at,
        ),
        searchable_columns=(
            schema.financial_news_chunks.c.chunk_id,
            schema.financial_news_chunks.c.article_id,
            schema.financial_news_chunks.c.title,
            schema.financial_news_chunks.c.text,
        ),
        order_column=schema.financial_news_chunks.c.created_at,
    ),
    "embeddings": EntityConfig(
        table=schema.financial_news_chunk_embeddings,
        id_column=schema.financial_news_chunk_embeddings.c.embedding_id,
        columns=(
            schema.financial_news_chunk_embeddings.c.embedding_id,
            schema.financial_news_chunk_embeddings.c.chunk_id,
            schema.financial_news_chunk_embeddings.c.article_id,
            schema.financial_news_chunk_embeddings.c.embedding_model,
            schema.financial_news_chunk_embeddings.c.embedding_dimension,
            schema.financial_news_chunk_embeddings.c.status,
            schema.financial_news_chunk_embeddings.c.error,
            schema.financial_news_chunk_embeddings.c.created_at,
        ),
        searchable_columns=(
            schema.financial_news_chunk_embeddings.c.embedding_id,
            schema.financial_news_chunk_embeddings.c.chunk_id,
            schema.financial_news_chunk_embeddings.c.article_id,
            schema.financial_news_chunk_embeddings.c.embedding_model,
        ),
        order_column=schema.financial_news_chunk_embeddings.c.created_at,
    ),
    "gold-labels": EntityConfig(
        table=schema.event_label_documents_gold,
        id_column=schema.event_label_documents_gold.c.article_id,
        columns=(
            schema.event_label_documents_gold.c.article_id,
            schema.event_label_documents_gold.c.document_label,
            schema.event_label_documents_gold.c.teacher_model,
            schema.event_label_documents_gold.c.prompt_version,
            schema.event_label_documents_gold.c.labeling_run_id,
            schema.event_label_documents_gold.c.updated_at,
        ),
        searchable_columns=(
            schema.event_label_documents_gold.c.article_id,
            schema.event_label_documents_gold.c.document_label,
            schema.event_label_documents_gold.c.teacher_model,
        ),
        order_column=schema.event_label_documents_gold.c.updated_at,
    ),
    "gold-events": EntityConfig(
        table=schema.events_gold,
        id_column=schema.events_gold.c.event_id,
        columns=(
            schema.events_gold.c.event_id,
            schema.events_gold.c.article_id,
            schema.events_gold.c.ticker,
            schema.events_gold.c.company_name,
            schema.events_gold.c.event_type,
            schema.events_gold.c.event_subtype,
            schema.events_gold.c.impact_sentiment,
            schema.events_gold.c.confidence,
            schema.events_gold.c.updated_at,
        ),
        searchable_columns=(
            schema.events_gold.c.event_id,
            schema.events_gold.c.article_id,
            schema.events_gold.c.ticker,
            schema.events_gold.c.company_name,
            schema.events_gold.c.event_type,
        ),
        order_column=schema.events_gold.c.updated_at,
    ),
    "patterns": EntityConfig(
        table=schema.event_patterns,
        id_column=schema.event_patterns.c.pattern_id,
        columns=(
            schema.event_patterns.c.pattern_id,
            schema.event_patterns.c.article_id,
            schema.event_patterns.c.pattern_kind,
            schema.event_patterns.c.event_type,
            schema.event_patterns.c.event_subtype,
            schema.event_patterns.c.ticker,
            schema.event_patterns.c.auto_validation_status,
            schema.event_patterns.c.updated_at,
        ),
        searchable_columns=(
            schema.event_patterns.c.pattern_id,
            schema.event_patterns.c.article_id,
            schema.event_patterns.c.event_type,
            schema.event_patterns.c.ticker,
            schema.event_patterns.c.pattern_text,
        ),
        order_column=schema.event_patterns.c.updated_at,
    ),
    "extraction-runs": EntityConfig(
        table=schema.extraction_runs,
        id_column=schema.extraction_runs.c.run_id,
        columns=(
            schema.extraction_runs.c.run_id,
            schema.extraction_runs.c.article_id,
            schema.extraction_runs.c.document_label,
            schema.extraction_runs.c.model_name,
            schema.extraction_runs.c.retrieval_config,
            schema.extraction_runs.c.run_dir,
            schema.extraction_runs.c.created_at,
            schema.extraction_runs.c.completed_at,
        ),
        searchable_columns=(
            schema.extraction_runs.c.run_id,
            schema.extraction_runs.c.article_id,
            schema.extraction_runs.c.model_name,
            schema.extraction_runs.c.retrieval_config,
        ),
        order_column=schema.extraction_runs.c.created_at,
    ),
    "node-traces": EntityConfig(
        table=schema.extraction_node_traces,
        id_column=schema.extraction_node_traces.c.trace_id,
        columns=(
            schema.extraction_node_traces.c.trace_id,
            schema.extraction_node_traces.c.run_id,
            schema.extraction_node_traces.c.node,
            schema.extraction_node_traces.c.status,
            schema.extraction_node_traces.c.latency_ms,
            schema.extraction_node_traces.c.created_at,
        ),
        searchable_columns=(
            schema.extraction_node_traces.c.run_id,
            schema.extraction_node_traces.c.node,
            schema.extraction_node_traces.c.status,
        ),
        order_column=schema.extraction_node_traces.c.created_at,
    ),
    "tickers": EntityConfig(
        table=schema.ticker_companies,
        id_column=schema.ticker_companies.c.ticker,
        columns=(
            schema.ticker_companies.c.ticker,
            schema.ticker_companies.c.company_name,
            schema.ticker_companies.c.sector,
            schema.ticker_companies.c.exchange,
            schema.ticker_companies.c.status,
            schema.ticker_companies.c.source_note,
            schema.ticker_companies.c.updated_at,
        ),
        searchable_columns=(
            schema.ticker_companies.c.ticker,
            schema.ticker_companies.c.company_name,
            schema.ticker_companies.c.sector,
            schema.ticker_companies.c.exchange,
        ),
        order_column=schema.ticker_companies.c.updated_at,
    ),
}


@router.get("/{entity}")
def list_entity_records(
    entity: str,
    query: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    config = _entity_config(entity)
    where_clause = _search_clause(config, query)
    count_statement = select(func.count()).select_from(config.table)
    statement = select(*config.columns)
    if where_clause is not None:
        count_statement = count_statement.where(where_clause)
        statement = statement.where(where_clause)
    if config.order_column is not None:
        statement = statement.order_by(config.order_column.desc())
    statement = statement.limit(limit).offset(offset)
    try:
        with get_sqlalchemy_engine().begin() as connection:
            total = int(connection.execute(count_statement).scalar() or 0)
            rows = [dict(row) for row in connection.execute(statement).mappings().all()]
    except Exception as exc:  # noqa: BLE001 - admin API should return a shaped 503.
        raise api_error(
            503,
            "DATABASE_QUERY_FAILED",
            "Database query failed.",
            details={"entity": entity, "error": str(exc)},
        ) from exc
    return {
        "entity": entity,
        "items": to_jsonable(rows),
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get("/{entity}/{record_id}")
def get_entity_record(entity: str, record_id: str) -> dict[str, Any]:
    config = _entity_config(entity)
    statement = select(config.table).where(config.id_column == record_id).limit(1)
    try:
        with get_sqlalchemy_engine().begin() as connection:
            row = connection.execute(statement).mappings().first()
    except Exception as exc:  # noqa: BLE001 - admin API should return a shaped 503.
        raise api_error(
            503,
            "DATABASE_QUERY_FAILED",
            "Database query failed.",
            details={"entity": entity, "record_id": record_id, "error": str(exc)},
        ) from exc
    if row is None:
        raise api_error(
            404,
            "DB_RECORD_NOT_FOUND",
            "Database record does not exist.",
            details={"entity": entity, "record_id": record_id},
        )
    data = dict(row)
    if "embedding" in data:
        data["embedding"] = "<vector omitted>"
    return {"entity": entity, "record": to_jsonable(data)}


def _entity_config(entity: str) -> EntityConfig:
    config = ENTITY_CONFIGS.get(entity)
    if config is None:
        raise api_error(
            404,
            "UNKNOWN_DB_ENTITY",
            "Unknown database browser entity.",
            details={"entity": entity, "allowed_entities": sorted(ENTITY_CONFIGS)},
        )
    return config


def _search_clause(config: EntityConfig, query: str | None) -> Any | None:
    if not query:
        return None
    pattern = f"%{query.lower()}%"
    return or_(
        *[
            func.lower(cast(column, String)).like(pattern)
            for column in config.searchable_columns
        ]
    )
