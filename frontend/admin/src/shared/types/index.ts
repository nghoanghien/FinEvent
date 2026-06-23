export type RunStatus = "queued" | "running" | "success" | "failed" | "canceled" | "interrupted";

export type HealthResponse = {
  api: string;
  postgres: string;
  pgvector: string;
  teacher_llm: string;
  student_llm: string;
  embedding: string;
  artifacts: {
    workspace_root: string;
    data_dir: boolean;
    reports_dir: boolean;
    runs_dir: boolean;
  };
};

export type WorkflowStep = {
  step_id: string;
  milestone: string;
  name: string;
  command: string[];
  expected_artifacts: string[];
  status: RunStatus;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  exit_code?: number | null;
  error_message?: string | null;
};

export type AdminRun = {
  run_id: string;
  workflow_name: string;
  status: RunStatus;
  config: Record<string, unknown>;
  steps: WorkflowStep[];
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  current_step_id?: string | null;
  summary: Record<string, unknown>;
  error_message?: string | null;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type CreateRunResponse = {
  run: AdminRun;
  detail_url: string;
};

export type LogEvent = {
  timestamp: string;
  run_id: string;
  step_id: string;
  level: "DEBUG" | "INFO" | "WARN" | "ERROR" | string;
  stream: "system" | "stdout" | "stderr" | string;
  message: string;
};

export type LogsResponse = Paginated<LogEvent> & {
  run_id: string;
};

export type ReportArtifact = {
  path: string;
  name: string;
  kind: "markdown" | "csv" | "jsonl" | "svg" | "image" | "json" | "text" | string;
  size_bytes: number;
  modified_at: string;
};

export type ReportTable = {
  columns: string[];
  rows: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
};

export type ReportJsonl = {
  rows: Record<string, unknown>[];
  parse_errors: string[];
  total: number;
  limit: number;
  offset: number;
};

export type ChartArtifact = {
  key: string;
  title: string;
  preferred_path: string;
  png_path?: string | null;
  svg_path?: string | null;
  source_tables: string[];
};

export type ChartGroup = {
  key: string;
  title: string;
  charts: ChartArtifact[];
};

export type ChartsResponse = {
  summary_paths: string[];
  final_dashboard?: string | null;
  groups: ChartGroup[];
};

export type DbEntity =
  | "articles"
  | "chunks"
  | "embeddings"
  | "gold-labels"
  | "gold-events"
  | "patterns"
  | "extraction-runs"
  | "node-traces"
  | "tickers";

export type DbListResponse = Paginated<Record<string, unknown>> & {
  entity: DbEntity;
};

export type DbDetailResponse = {
  entity: DbEntity;
  record: Record<string, unknown>;
};

export type OutputSummary = {
  run_id: string;
  article_id?: string | null;
  document_label?: string | null;
  model_name?: string | null;
  retrieval_config?: string | null;
  run_dir?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
};

export type OutputsResponse = Paginated<OutputSummary> & {
  source: "postgres" | "filesystem";
};

export type StructuredOutput = {
  source: "postgres" | "filesystem";
  path?: string;
  run_id?: string;
  article_id?: string | null;
  prediction?: Record<string, unknown>;
  output?: Record<string, unknown>;
  draft_output?: Record<string, unknown>;
  validation_issues?: unknown[];
  verification_report?: Record<string, unknown>;
  hallucination_metrics?: Record<string, unknown>;
  node_traces?: Record<string, unknown>[];
  run?: Record<string, unknown>;
};

export type WorkflowPreset = {
  id: "student_batch_extraction" | "student_batch_with_evaluation" | "evaluation";
  title: string;
  description: string;
  accent: "emerald" | "sky" | "amber";
  defaultConfig: Record<string, unknown>;
};

export type ApiRuntimeConfig = {
  baseUrl: string;
  adminApiKey: string;
};
