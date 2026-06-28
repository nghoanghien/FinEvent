CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS financial_news_documents (
    article_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    published_at TIMESTAMPTZ,
    content_hash TEXT,
    language TEXT NOT NULL DEFAULT 'vi',
    tickers_hint JSONB NOT NULL DEFAULT '[]'::jsonb,
    company_names_hint JSONB NOT NULL DEFAULT '[]'::jsonb,
    sector_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_type_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_subtype_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_news_chunks (
    chunk_id TEXT PRIMARY KEY,
    article_id TEXT NOT NULL REFERENCES financial_news_documents(article_id) ON DELETE CASCADE,
    chunk_level TEXT NOT NULL CHECK (chunk_level IN ('document', 'section', 'paragraph')),
    chunk_index INTEGER NOT NULL,
    parent_chunk_id TEXT,
    text TEXT NOT NULL,
    title TEXT,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    content_hash TEXT,
    chunk_hash TEXT NOT NULL,
    text_word_count INTEGER NOT NULL,
    tickers_hint JSONB NOT NULL DEFAULT '[]'::jsonb,
    company_names_hint JSONB NOT NULL DEFAULT '[]'::jsonb,
    sector_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_type_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_subtype_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    pattern_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    paragraph_start INTEGER,
    paragraph_end INTEGER,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version TEXT NOT NULL DEFAULT 'm03_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (article_id, chunk_level, chunk_index)
);

CREATE TABLE IF NOT EXISTS financial_news_chunk_patterns (
    chunk_id TEXT NOT NULL REFERENCES financial_news_chunks(chunk_id) ON DELETE CASCADE,
    article_id TEXT NOT NULL,
    pattern_id TEXT NOT NULL,
    event_id TEXT,
    event_type TEXT,
    event_subtype TEXT,
    pattern_kind TEXT,
    document_label TEXT,
    match_strategy TEXT NOT NULL,
    match_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    pattern_ref JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (chunk_id, pattern_id)
);

CREATE TABLE IF NOT EXISTS financial_news_chunk_embeddings (
    embedding_id TEXT PRIMARY KEY,
    chunk_id TEXT NOT NULL REFERENCES financial_news_chunks(chunk_id) ON DELETE CASCADE,
    article_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    content_hash TEXT,
    chunk_hash TEXT NOT NULL,
    embedding VECTOR,
    status TEXT NOT NULL DEFAULT 'success',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chunk_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_financial_news_documents_source
    ON financial_news_documents(source);
CREATE INDEX IF NOT EXISTS idx_financial_news_documents_published_at
    ON financial_news_documents(published_at);
CREATE INDEX IF NOT EXISTS idx_financial_news_documents_tickers
    ON financial_news_documents USING GIN (tickers_hint);

CREATE INDEX IF NOT EXISTS idx_financial_news_chunks_article_id
    ON financial_news_chunks(article_id);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunks_level
    ON financial_news_chunks(chunk_level);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunks_tickers
    ON financial_news_chunks USING GIN (tickers_hint);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunks_event_keywords
    ON financial_news_chunks USING GIN (event_keywords);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunks_event_types
    ON financial_news_chunks USING GIN (event_type_hints);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunks_pattern_refs
    ON financial_news_chunks USING GIN (pattern_refs);

CREATE INDEX IF NOT EXISTS idx_financial_news_chunk_patterns_article_id
    ON financial_news_chunk_patterns(article_id);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunk_patterns_pattern_id
    ON financial_news_chunk_patterns(pattern_id);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunk_patterns_event_type
    ON financial_news_chunk_patterns(event_type);

CREATE INDEX IF NOT EXISTS idx_financial_news_chunk_embeddings_chunk_id
    ON financial_news_chunk_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_financial_news_chunk_embeddings_model
    ON financial_news_chunk_embeddings(embedding_model);
