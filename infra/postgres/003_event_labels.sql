CREATE TABLE IF NOT EXISTS event_labeling_runs (
    labeling_run_id TEXT PRIMARY KEY,
    label_schema_version TEXT NOT NULL,
    teacher_model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    source_path TEXT,
    gold_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS event_label_documents_gold (
    article_id TEXT PRIMARY KEY,
    document_label TEXT NOT NULL CHECK (document_label IN ('HAS_EVENT', 'NO_EVENT', 'UNCERTAIN')),
    label_reason TEXT NOT NULL,
    label_schema_version TEXT NOT NULL,
    label_source TEXT NOT NULL DEFAULT 'ai_generated',
    teacher_model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    labeling_run_id TEXT REFERENCES event_labeling_runs(labeling_run_id),
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_info JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw_label JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events_gold (
    event_id TEXT PRIMARY KEY,
    article_id TEXT NOT NULL REFERENCES event_label_documents_gold(article_id) ON DELETE CASCADE,
    ticker TEXT,
    company_name TEXT,
    event_type TEXT NOT NULL,
    event_subtype TEXT,
    event_summary TEXT NOT NULL,
    event_reason TEXT NOT NULL,
    event_arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    impact_sentiment TEXT NOT NULL CHECK (impact_sentiment IN ('POSITIVE', 'NEGATIVE', 'NEUTRAL', 'MIXED')),
    evidence_span TEXT NOT NULL,
    source_url TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    label_schema_version TEXT NOT NULL,
    label_source TEXT NOT NULL DEFAULT 'ai_generated',
    teacher_model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    labeling_run_id TEXT REFERENCES event_labeling_runs(labeling_run_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_label_rejections (
    rejection_id BIGSERIAL PRIMARY KEY,
    article_id TEXT,
    label_schema_version TEXT NOT NULL,
    teacher_model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    labeling_run_id TEXT REFERENCES event_labeling_runs(labeling_run_id),
    validation_errors JSONB NOT NULL,
    raw_output JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_label_documents_gold_document_label
    ON event_label_documents_gold(document_label);
CREATE INDEX IF NOT EXISTS idx_events_gold_article_id
    ON events_gold(article_id);
CREATE INDEX IF NOT EXISTS idx_events_gold_ticker
    ON events_gold(ticker);
CREATE INDEX IF NOT EXISTS idx_events_gold_event_type
    ON events_gold(event_type);
CREATE INDEX IF NOT EXISTS idx_events_gold_event_subtype
    ON events_gold(event_subtype);
CREATE INDEX IF NOT EXISTS idx_events_gold_impact_sentiment
    ON events_gold(impact_sentiment);
CREATE INDEX IF NOT EXISTS idx_events_gold_event_arguments
    ON events_gold USING GIN (event_arguments);
