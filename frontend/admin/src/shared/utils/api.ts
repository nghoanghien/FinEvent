"use client";

import { http } from "./http";
import type {
  AdminRun,
  ChartsResponse,
  CreateRunResponse,
  DbDetailResponse,
  DbEntity,
  DbListResponse,
  HealthResponse,
  LogsResponse,
  OutputsResponse,
  Paginated,
  ReportArtifact,
  ReportJsonl,
  ReportTable,
  StructuredOutput,
} from "../types";

// Re-export core HTTP exports so existing references do not break
export { http, AdminApiError, toApiError } from "./http";

/**
 * Admin API Endpoints
 * Handles all admin panel data fetching and mutations
 */
export const adminApi = {
  /**
   * Health check
   * GET /admin/health
   */
  health: () => {
    return http.get<HealthResponse>("/admin/health") as unknown as Promise<HealthResponse>;
  },

  /**
   * List all runs with optional filters
   * GET /admin/runs
   */
  listRuns: (query?: { status?: string; workflow_name?: string; limit?: number; offset?: number }) => {
    return http.get<Paginated<AdminRun>>("/admin/runs", {
      params: query,
    }) as unknown as Promise<Paginated<AdminRun>>;
  },

  /**
   * Create a new workflow run
   * POST /admin/runs
   */
  createRun: (workflow_name: string, config: Record<string, unknown>) => {
    return http.post<CreateRunResponse>("/admin/runs", {
      workflow_name,
      config,
    }) as unknown as Promise<CreateRunResponse>;
  },

  /**
   * Get run details by ID
   * GET /admin/runs/:runId
   */
  getRun: (runId: string) => {
    return http.get<AdminRun>(
      `/admin/runs/${encodeURIComponent(runId)}`,
    ) as unknown as Promise<AdminRun>;
  },

  /**
   * Cancel a running workflow
   * POST /admin/runs/:runId/cancel
   */
  cancelRun: (runId: string) => {
    return http.post<AdminRun>(
      `/admin/runs/${encodeURIComponent(runId)}/cancel`,
    ) as unknown as Promise<AdminRun>;
  },

  /**
   * Get logs for a specific run
   * GET /admin/runs/:runId/logs
   */
  logs: (runId: string, query?: { limit?: number; offset?: number; level?: string; step_id?: string }) => {
    return http.get<LogsResponse>(`/admin/runs/${encodeURIComponent(runId)}/logs`, {
      params: query,
    }) as unknown as Promise<LogsResponse>;
  },

  /**
   * List report artifacts
   * GET /admin/reports
   */
  reports: (query?: { kind?: string; limit?: number; offset?: number }) => {
    return http.get<Paginated<ReportArtifact>>("/admin/reports", {
      params: query,
    }) as unknown as Promise<Paginated<ReportArtifact>>;
  },

  /**
   * Get report content as text (markdown, plain text, etc.)
   * GET /admin/reports/content
   */
  reportContent: (path: string) => {
    return http.get<string>("/admin/reports/content", {
      params: { path },
      headers: { Accept: "text/plain, text/markdown, application/json" },
      responseType: "text",
    }) as unknown as Promise<string>;
  },

  /**
   * Get report as structured table
   * GET /admin/reports/table
   */
  reportTable: (path: string, query?: { limit?: number; offset?: number }) => {
    return http.get<ReportTable>("/admin/reports/table", {
      params: { path, ...query },
    }) as unknown as Promise<ReportTable>;
  },

  /**
   * Get report as JSONL
   * GET /admin/reports/jsonl
   */
  reportJsonl: (path: string, query?: { limit?: number; offset?: number }) => {
    return http.get<ReportJsonl>("/admin/reports/jsonl", {
      params: { path, ...query },
    }) as unknown as Promise<ReportJsonl>;
  },

  /**
   * Download report as binary blob
   * GET /admin/reports/content
   */
  reportBlob: (path: string) => {
    return http.get<Blob>("/admin/reports/content", {
      params: { path },
      headers: { Accept: "*/*" },
      responseType: "blob",
    }) as unknown as Promise<Blob>;
  },

  /**
   * Get chart data for dashboard
   * GET /admin/reports/charts
   */
  charts: () => {
    return http.get<ChartsResponse>(
      "/admin/reports/charts",
    ) as unknown as Promise<ChartsResponse>;
  },

  /**
   * List database entities
   * GET /admin/db/:entity
   */
  dbList: (entity: DbEntity, query?: { query?: string; limit?: number; offset?: number }) => {
    return http.get<DbListResponse>(`/admin/db/${entity}`, {
      params: query,
    }) as unknown as Promise<DbListResponse>;
  },

  /**
   * Get detail of a specific database record
   * GET /admin/db/:entity/:recordId
   */
  dbDetail: (entity: DbEntity, recordId: string) => {
    return http.get<DbDetailResponse>(
      `/admin/db/${entity}/${encodeURIComponent(recordId)}`,
    ) as unknown as Promise<DbDetailResponse>;
  },

  /**
   * List structured outputs
   * GET /admin/outputs
   */
  outputs: (query?: { article_id?: string; source?: string; limit?: number; offset?: number }) => {
    return http.get<OutputsResponse>("/admin/outputs", {
      params: query,
    }) as unknown as Promise<OutputsResponse>;
  },

  /**
   * Get output detail by run ID
   * GET /admin/outputs/:runId
   */
  output: (runId: string) => {
    return http.get<StructuredOutput>(
      `/admin/outputs/${encodeURIComponent(runId)}`,
    ) as unknown as Promise<StructuredOutput>;
  },

  /**
   * Get output by article ID
   * GET /admin/outputs/by-article/:articleId
   */
  outputByArticle: (articleId: string) => {
    return http.get<StructuredOutput>(
      `/admin/outputs/by-article/${encodeURIComponent(articleId)}`,
    ) as unknown as Promise<StructuredOutput>;
  },
};
