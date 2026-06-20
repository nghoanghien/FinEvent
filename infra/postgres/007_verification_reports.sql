ALTER TABLE extraction_runs
    ADD COLUMN IF NOT EXISTS draft_output JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS verification_report JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS hallucination_metrics JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_extraction_runs_verification_report
    ON extraction_runs USING GIN (verification_report);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_hallucination_metrics
    ON extraction_runs USING GIN (hallucination_metrics);
