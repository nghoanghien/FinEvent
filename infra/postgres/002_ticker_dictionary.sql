CREATE TABLE IF NOT EXISTS ticker_companies (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT,
    exchange TEXT NOT NULL DEFAULT 'UNKNOWN',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_note TEXT,
    source_url TEXT,
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ticker_companies_ticker_format CHECK (ticker ~ '^[A-Z0-9]{2,10}$')
);

CREATE TABLE IF NOT EXISTS ticker_company_aliases (
    alias_id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL REFERENCES ticker_companies(ticker) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_norm TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticker, alias_norm)
);

CREATE TABLE IF NOT EXISTS ticker_dictionary_sync_runs (
    sync_run_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_path TEXT,
    upserted_companies INTEGER NOT NULL DEFAULT 0,
    upserted_aliases INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_ticker_companies_sector ON ticker_companies(sector);
CREATE INDEX IF NOT EXISTS idx_ticker_companies_exchange ON ticker_companies(exchange);
CREATE INDEX IF NOT EXISTS idx_ticker_company_aliases_alias_norm
    ON ticker_company_aliases(alias_norm);

CREATE OR REPLACE VIEW ticker_company_search AS
SELECT
    c.ticker,
    c.company_name,
    c.sector,
    c.exchange,
    c.status,
    c.source_note,
    c.source_url,
    c.last_verified_at,
    COALESCE(jsonb_agg(a.alias ORDER BY a.alias) FILTER (WHERE a.alias IS NOT NULL), '[]'::jsonb)
        AS aliases
FROM ticker_companies c
LEFT JOIN ticker_company_aliases a ON a.ticker = c.ticker
GROUP BY
    c.ticker,
    c.company_name,
    c.sector,
    c.exchange,
    c.status,
    c.source_note,
    c.source_url,
    c.last_verified_at;
