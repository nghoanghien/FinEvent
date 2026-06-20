"""SQLAlchemy Core metadata for FinEvent-VN tables.

The current workflow sync modules may keep using raw SQL for explicit upserts
and pgvector literals. This metadata centralizes table definitions for Alembic,
API queries, and future repository/ORM layers.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_: object) -> str:
        return "VECTOR"


metadata = MetaData()


articles = Table(
    "articles",
    metadata,
    Column("article_id", Text, primary_key=True),
    Column("source", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("title", Text),
    Column("published_at", TIMESTAMP(timezone=True)),
    Column("author", Text),
    Column("clean_text_path", Text),
    Column("content_hash", Text),
    Column("language", Text, server_default=text("'vi'")),
    Column("created_at", TIMESTAMP(timezone=True), server_default=text("NOW()")),
)

article_metadata = Table(
    "article_metadata",
    metadata,
    Column(
        "article_id",
        Text,
        ForeignKey("articles.article_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("tickers_hint", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("company_names_hint", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("sector_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_keywords", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_type_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_subtype_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("metadata_confidence", Float),
    Column("parse_warnings", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
)

ticker_companies = Table(
    "ticker_companies",
    metadata,
    Column("ticker", Text, primary_key=True),
    Column("company_name", Text, nullable=False),
    Column("sector", Text),
    Column("exchange", Text, nullable=False, server_default=text("'UNKNOWN'")),
    Column("status", Text, nullable=False, server_default=text("'ACTIVE'")),
    Column("source_note", Text),
    Column("source_url", Text),
    Column("last_verified_at", TIMESTAMP(timezone=True)),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint("ticker ~ '^[A-Z0-9]{2,10}$'", name="ticker_companies_ticker_format"),
)

ticker_company_aliases = Table(
    "ticker_company_aliases",
    metadata,
    Column("alias_id", BigInteger, primary_key=True),
    Column(
        "ticker",
        Text,
        ForeignKey("ticker_companies.ticker", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("alias", Text, nullable=False),
    Column("alias_norm", Text, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    UniqueConstraint("ticker", "alias_norm"),
)

ticker_dictionary_sync_runs = Table(
    "ticker_dictionary_sync_runs",
    metadata,
    Column("sync_run_id", Text, primary_key=True),
    Column("source_type", Text, nullable=False),
    Column("source_path", Text),
    Column("upserted_companies", Integer, nullable=False, server_default=text("0")),
    Column("upserted_aliases", Integer, nullable=False, server_default=text("0")),
    Column("started_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("completed_at", TIMESTAMP(timezone=True)),
    Column("status", Text, nullable=False, server_default=text("'RUNNING'")),
    Column("error", Text),
)

event_labeling_runs = Table(
    "event_labeling_runs",
    metadata,
    Column("labeling_run_id", Text, primary_key=True),
    Column("label_schema_version", Text, nullable=False),
    Column("teacher_model", Text, nullable=False),
    Column("prompt_version", Text, nullable=False),
    Column("source_path", Text),
    Column("gold_count", Integer, nullable=False, server_default=text("0")),
    Column("rejected_count", Integer, nullable=False, server_default=text("0")),
    Column("status", Text, nullable=False, server_default=text("'RUNNING'")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("completed_at", TIMESTAMP(timezone=True)),
)

event_label_documents_gold = Table(
    "event_label_documents_gold",
    metadata,
    Column("article_id", Text, primary_key=True),
    Column("document_label", Text, nullable=False),
    Column("label_schema_version", Text, nullable=False),
    Column("label_source", Text, nullable=False, server_default=text("'ai_generated'")),
    Column("teacher_model", Text, nullable=False),
    Column("prompt_version", Text, nullable=False),
    Column("labeling_run_id", Text, ForeignKey("event_labeling_runs.labeling_run_id")),
    Column("warnings", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("model_info", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("validation_warnings", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("raw_label", JSONB, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint("document_label IN ('HAS_EVENT', 'NO_EVENT', 'UNCERTAIN')"),
)

events_gold = Table(
    "events_gold",
    metadata,
    Column("event_id", Text, primary_key=True),
    Column(
        "article_id",
        Text,
        ForeignKey("event_label_documents_gold.article_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("ticker", Text),
    Column("company_name", Text),
    Column("event_type", Text, nullable=False),
    Column("event_subtype", Text),
    Column("event_summary", Text, nullable=False),
    Column("event_arguments", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("impact_sentiment", Text, nullable=False),
    Column("evidence_span", Text, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("published_at", TIMESTAMP(timezone=True)),
    Column("confidence", Float, nullable=False),
    Column("label_schema_version", Text, nullable=False),
    Column("label_source", Text, nullable=False, server_default=text("'ai_generated'")),
    Column("teacher_model", Text, nullable=False),
    Column("prompt_version", Text, nullable=False),
    Column("labeling_run_id", Text, ForeignKey("event_labeling_runs.labeling_run_id")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint("impact_sentiment IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL', 'MIXED')"),
    CheckConstraint("confidence >= 0 AND confidence <= 1"),
)

event_label_rejections = Table(
    "event_label_rejections",
    metadata,
    Column("rejection_id", BigInteger, primary_key=True),
    Column("article_id", Text),
    Column("label_schema_version", Text, nullable=False),
    Column("teacher_model", Text, nullable=False),
    Column("prompt_version", Text, nullable=False),
    Column("labeling_run_id", Text, ForeignKey("event_labeling_runs.labeling_run_id")),
    Column("validation_errors", JSONB, nullable=False),
    Column("raw_output", JSONB),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
)

financial_news_documents = Table(
    "financial_news_documents",
    metadata,
    Column("article_id", Text, primary_key=True),
    Column("source", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("title", Text),
    Column("published_at", TIMESTAMP(timezone=True)),
    Column("content_hash", Text),
    Column("language", Text, nullable=False, server_default=text("'vi'")),
    Column("tickers_hint", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("company_names_hint", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("sector_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_keywords", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_type_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_subtype_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
)

financial_news_chunks = Table(
    "financial_news_chunks",
    metadata,
    Column("chunk_id", Text, primary_key=True),
    Column(
        "article_id",
        Text,
        ForeignKey("financial_news_documents.article_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("chunk_level", Text, nullable=False),
    Column("chunk_index", Integer, nullable=False),
    Column("parent_chunk_id", Text),
    Column("text", Text, nullable=False),
    Column("title", Text),
    Column("source", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("published_at", TIMESTAMP(timezone=True)),
    Column("content_hash", Text),
    Column("chunk_hash", Text, nullable=False),
    Column("text_word_count", Integer, nullable=False),
    Column("tickers_hint", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("company_names_hint", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("sector_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_keywords", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_type_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("event_subtype_hints", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("paragraph_start", Integer),
    Column("paragraph_end", Integer),
    Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("version", Text, nullable=False, server_default=text("'m03_v1'")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    UniqueConstraint("article_id", "chunk_level", "chunk_index"),
    CheckConstraint("chunk_level IN ('document', 'section', 'paragraph')"),
)

financial_news_chunk_embeddings = Table(
    "financial_news_chunk_embeddings",
    metadata,
    Column("embedding_id", Text, primary_key=True),
    Column(
        "chunk_id",
        Text,
        ForeignKey("financial_news_chunks.chunk_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("article_id", Text, nullable=False),
    Column("embedding_model", Text, nullable=False),
    Column("embedding_dimension", Integer, nullable=False),
    Column("content_hash", Text),
    Column("chunk_hash", Text, nullable=False),
    Column("embedding", Vector()),
    Column("status", Text, nullable=False, server_default=text("'success'")),
    Column("error", Text),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    UniqueConstraint("chunk_id", "embedding_model"),
)

event_patterns = Table(
    "event_patterns",
    metadata,
    Column("pattern_id", Text, primary_key=True),
    Column("article_id", Text, nullable=False),
    Column("document_label", Text, nullable=False),
    Column("pattern_kind", Text, nullable=False),
    Column("event_id", Text),
    Column("event_type", Text),
    Column("event_subtype", Text),
    Column("ticker", Text),
    Column("company_name", Text),
    Column("impact_sentiment", Text),
    Column("input_excerpt", Text, nullable=False),
    Column("gold_output", JSONB, nullable=False),
    Column("pattern_text", Text, nullable=False),
    Column("evidence_span", Text),
    Column("event_arguments", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("explanation_brief", Text, nullable=False, server_default=text("''")),
    Column("source", Text, nullable=False, server_default=text("''")),
    Column("url", Text, nullable=False, server_default=text("''")),
    Column("published_at", TIMESTAMP(timezone=True)),
    Column("teacher_model", Text, nullable=False),
    Column("teacher_prompt_version", Text, nullable=False, server_default=text("''")),
    Column("auto_validation_status", Text, nullable=False, server_default=text("'PASS'")),
    Column("validation_errors", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("version", Text, nullable=False, server_default=text("'m05_v1'")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    CheckConstraint("document_label IN ('HAS_EVENT', 'NO_EVENT')"),
    CheckConstraint("pattern_kind IN ('event', 'no_event')"),
)

event_pattern_embeddings = Table(
    "event_pattern_embeddings",
    metadata,
    Column("embedding_id", Text, primary_key=True),
    Column(
        "pattern_id",
        Text,
        ForeignKey("event_patterns.pattern_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("embedding_model", Text, nullable=False),
    Column("embedding_dimension", Integer, nullable=False),
    Column("pattern_hash", Text, nullable=False),
    Column("embedding", Vector()),
    Column("status", Text, nullable=False, server_default=text("'success'")),
    Column("error", Text),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    UniqueConstraint("pattern_id", "embedding_model"),
)

extraction_runs = Table(
    "extraction_runs",
    metadata,
    Column("run_id", Text, primary_key=True),
    Column("article_id", Text),
    Column("document_label", Text),
    Column("workflow_config", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("model_name", Text, nullable=False),
    Column("prompt_version", Text, nullable=False),
    Column("retrieval_config", Text),
    Column("pattern_ids", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("final_output", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("validation_issues", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("warnings", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("errors", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("run_dir", Text),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
    Column("completed_at", TIMESTAMP(timezone=True)),
)

extraction_node_traces = Table(
    "extraction_node_traces",
    metadata,
    Column("trace_id", BigInteger, primary_key=True),
    Column(
        "run_id",
        Text,
        ForeignKey("extraction_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("node", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("latency_ms", Float, nullable=False, server_default=text("0")),
    Column("input_summary", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("output_summary", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("warnings", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("errors", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=text("NOW()")),
)

Index("idx_articles_source", articles.c.source)
Index("idx_articles_published_at", articles.c.published_at)
Index("idx_ticker_companies_sector", ticker_companies.c.sector)
Index("idx_ticker_companies_exchange", ticker_companies.c.exchange)
Index("idx_events_gold_event_type", events_gold.c.event_type)
Index("idx_financial_news_chunks_article_id", financial_news_chunks.c.article_id)
Index("idx_event_patterns_event_type", event_patterns.c.event_type)
Index("idx_extraction_runs_article_id", extraction_runs.c.article_id)
