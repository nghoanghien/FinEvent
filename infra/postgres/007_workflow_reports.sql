CREATE TABLE IF NOT EXISTS workflow_reports (
    report_id TEXT PRIMARY KEY,
    run_id TEXT,
    workflow_name TEXT,
    step_id TEXT,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    content_text TEXT,
    content_json JSONB,
    content_truncated BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_reports_run_id
    ON workflow_reports(run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_reports_workflow_name
    ON workflow_reports(workflow_name);
CREATE INDEX IF NOT EXISTS idx_workflow_reports_step_id
    ON workflow_reports(step_id);
CREATE INDEX IF NOT EXISTS idx_workflow_reports_path
    ON workflow_reports(path);
CREATE INDEX IF NOT EXISTS idx_workflow_reports_kind
    ON workflow_reports(kind);
CREATE INDEX IF NOT EXISTS idx_workflow_reports_updated_at
    ON workflow_reports(updated_at);
