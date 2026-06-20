CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    article_id TEXT,
    document_label TEXT,
    workflow_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    retrieval_config TEXT,
    pattern_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    final_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    run_dir TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS extraction_node_traces (
    trace_id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES extraction_runs(run_id) ON DELETE CASCADE,
    node TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
    input_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extraction_runs_article_id
    ON extraction_runs(article_id);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_document_label
    ON extraction_runs(document_label);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_model_name
    ON extraction_runs(model_name);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_created_at
    ON extraction_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_final_output
    ON extraction_runs USING GIN (final_output);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_validation_issues
    ON extraction_runs USING GIN (validation_issues);

CREATE INDEX IF NOT EXISTS idx_extraction_node_traces_run_id
    ON extraction_node_traces(run_id);
CREATE INDEX IF NOT EXISTS idx_extraction_node_traces_node
    ON extraction_node_traces(node);
