CREATE TABLE IF NOT EXISTS event_patterns (
    pattern_id TEXT PRIMARY KEY,
    article_id TEXT NOT NULL,
    document_label TEXT NOT NULL CHECK (document_label IN ('HAS_EVENT', 'NO_EVENT')),
    pattern_kind TEXT NOT NULL CHECK (pattern_kind IN ('event', 'no_event')),
    event_id TEXT,
    event_type TEXT,
    event_subtype TEXT,
    ticker TEXT,
    company_name TEXT,
    impact_sentiment TEXT,
    input_excerpt TEXT NOT NULL,
    gold_output JSONB NOT NULL,
    pattern_text TEXT NOT NULL,
    evidence_span TEXT,
    event_arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    explanation_brief TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    published_at TIMESTAMPTZ,
    teacher_model TEXT NOT NULL,
    teacher_prompt_version TEXT NOT NULL DEFAULT '',
    auto_validation_status TEXT NOT NULL DEFAULT 'PASS',
    validation_errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    version TEXT NOT NULL DEFAULT 'm05_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_patterns_article_id
    ON event_patterns(article_id);
CREATE INDEX IF NOT EXISTS idx_event_patterns_document_label
    ON event_patterns(document_label);
CREATE INDEX IF NOT EXISTS idx_event_patterns_event_type
    ON event_patterns(event_type);
CREATE INDEX IF NOT EXISTS idx_event_patterns_event_subtype
    ON event_patterns(event_subtype);
CREATE INDEX IF NOT EXISTS idx_event_patterns_ticker
    ON event_patterns(ticker);
CREATE INDEX IF NOT EXISTS idx_event_patterns_published_at
    ON event_patterns(published_at);
CREATE INDEX IF NOT EXISTS idx_event_patterns_gold_output
    ON event_patterns USING GIN (gold_output);
CREATE INDEX IF NOT EXISTS idx_event_patterns_metadata
    ON event_patterns USING GIN (metadata);
