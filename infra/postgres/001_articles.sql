CREATE TABLE IF NOT EXISTS articles (
    article_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    raw_html_path TEXT,
    title TEXT,
    published_at TIMESTAMPTZ,
    author TEXT,
    clean_text_path TEXT,
    content_hash TEXT,
    language TEXT DEFAULT 'vi',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS article_metadata (
    article_id TEXT PRIMARY KEY REFERENCES articles(article_id) ON DELETE CASCADE,
    tickers_hint JSONB NOT NULL DEFAULT '[]'::jsonb,
    company_names_hint JSONB NOT NULL DEFAULT '[]'::jsonb,
    sector_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_type_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    event_subtype_hints JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata_confidence REAL,
    parse_warnings JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at);
CREATE INDEX IF NOT EXISTS idx_article_metadata_tickers
    ON article_metadata USING GIN (tickers_hint);
CREATE INDEX IF NOT EXISTS idx_article_metadata_event_types
    ON article_metadata USING GIN (event_type_hints);
