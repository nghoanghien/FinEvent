CREATE TABLE IF NOT EXISTS retrieval_runs (
    retrieval_run_id TEXT PRIMARY KEY,
    article_id TEXT,
    retrieval_config TEXT NOT NULL,
    query_plan JSONB NOT NULL DEFAULT '[]'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_path TEXT,
    output_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS retrieval_run_contexts (
    retrieval_run_id TEXT NOT NULL REFERENCES retrieval_runs(retrieval_run_id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    chunk_id TEXT NOT NULL,
    article_id TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0,
    score_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    pattern_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (retrieval_run_id, rank)
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id TEXT PRIMARY KEY,
    article_id TEXT,
    document_label TEXT,
    workflow_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    retrieval_config TEXT,
    pattern_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    retrieval_run_id TEXT,
    context_chunk_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    draft_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    final_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning_trace JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    hallucination_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    run_dir TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_retrieval_runs_article_id
    ON retrieval_runs(article_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_runs_config
    ON retrieval_runs(retrieval_config);
CREATE INDEX IF NOT EXISTS idx_retrieval_runs_created_at
    ON retrieval_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_retrieval_run_contexts_run_id
    ON retrieval_run_contexts(retrieval_run_id);
CREATE INDEX IF NOT EXISTS idx_retrieval_run_contexts_chunk_id
    ON retrieval_run_contexts(chunk_id);

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
CREATE INDEX IF NOT EXISTS idx_extraction_runs_reasoning_trace
    ON extraction_runs USING GIN (reasoning_trace);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_validation_issues
    ON extraction_runs USING GIN (validation_issues);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_verification_report
    ON extraction_runs USING GIN (verification_report);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_hallucination_metrics
    ON extraction_runs USING GIN (hallucination_metrics);

CREATE INDEX IF NOT EXISTS idx_extraction_node_traces_run_id
    ON extraction_node_traces(run_id);
CREATE INDEX IF NOT EXISTS idx_extraction_node_traces_node
    ON extraction_node_traces(node);
