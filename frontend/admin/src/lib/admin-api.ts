"use client";

import { getStoredConfig } from "./config";
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
} from "./types";

type QueryValue = string | number | boolean | null | undefined;

export class AdminApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function buildUrl(path: string, query?: Record<string, QueryValue>) {
  const config = getStoredConfig();
  const baseUrl = config.baseUrl.replace(/\/$/, "");
  const url = new URL(path.startsWith("/") ? `${baseUrl}${path}` : `${baseUrl}/${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

export function adminHeaders(extra?: HeadersInit): HeadersInit {
  const config = getStoredConfig();
  return {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...(config.adminApiKey ? { "X-Admin-API-Key": config.adminApiKey } : {}),
    ...extra,
  };
}

export async function adminFetch<T>(
  path: string,
  options: RequestInit & { query?: Record<string, QueryValue> } = {},
): Promise<T> {
  const { query, headers, ...init } = options;
  const response = await fetch(buildUrl(path, query), {
    ...init,
    headers: adminHeaders(headers),
    cache: "no-store",
  });
  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function adminFetchText(path: string, query?: Record<string, QueryValue>) {
  const response = await fetch(buildUrl(path, query), {
    headers: adminHeaders({ Accept: "text/plain, text/markdown, application/json" }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return response.text();
}

export async function adminFetchBlob(path: string, query?: Record<string, QueryValue>) {
  const response = await fetch(buildUrl(path, query), {
    headers: adminHeaders({ Accept: "*/*" }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return response.blob();
}

async function toApiError(response: Response) {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = await response.text().catch(() => null);
  }
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    return new AdminApiError(
      String(record.message || record.detail || response.statusText),
      response.status,
      typeof record.error_code === "string" ? record.error_code : undefined,
      record.details,
    );
  }
  return new AdminApiError(String(payload || response.statusText), response.status);
}

export const adminApi = {
  health: () => adminFetch<HealthResponse>("/admin/health"),
  listRuns: (query?: { status?: string; workflow_name?: string; limit?: number; offset?: number }) =>
    adminFetch<Paginated<AdminRun>>("/admin/runs", { query }),
  createRun: (workflow_name: string, config: Record<string, unknown>) =>
    adminFetch<CreateRunResponse>("/admin/runs", {
      method: "POST",
      body: JSON.stringify({ workflow_name, config }),
    }),
  getRun: (runId: string) => adminFetch<AdminRun>(`/admin/runs/${encodeURIComponent(runId)}`),
  cancelRun: (runId: string) =>
    adminFetch<AdminRun>(`/admin/runs/${encodeURIComponent(runId)}/cancel`, {
      method: "POST",
    }),
  logs: (runId: string, query?: { limit?: number; offset?: number; level?: string; step_id?: string }) =>
    adminFetch<LogsResponse>(`/admin/runs/${encodeURIComponent(runId)}/logs`, { query }),
  reports: (query?: { kind?: string; limit?: number; offset?: number }) =>
    adminFetch<Paginated<ReportArtifact>>("/admin/reports", { query }),
  reportContent: (path: string) => adminFetchText("/admin/reports/content", { path }),
  reportTable: (path: string, query?: { limit?: number; offset?: number }) =>
    adminFetch<ReportTable>("/admin/reports/table", { query: { path, ...query } }),
  reportJsonl: (path: string, query?: { limit?: number; offset?: number }) =>
    adminFetch<ReportJsonl>("/admin/reports/jsonl", { query: { path, ...query } }),
  reportBlob: (path: string) => adminFetchBlob("/admin/reports/content", { path }),
  charts: () => adminFetch<ChartsResponse>("/admin/reports/charts"),
  dbList: (entity: DbEntity, query?: { query?: string; limit?: number; offset?: number }) =>
    adminFetch<DbListResponse>(`/admin/db/${entity}`, { query }),
  dbDetail: (entity: DbEntity, recordId: string) =>
    adminFetch<DbDetailResponse>(`/admin/db/${entity}/${encodeURIComponent(recordId)}`),
  outputs: (query?: { article_id?: string; source?: string; limit?: number; offset?: number }) =>
    adminFetch<OutputsResponse>("/admin/outputs", { query }),
  output: (runId: string) => adminFetch<StructuredOutput>(`/admin/outputs/${encodeURIComponent(runId)}`),
  outputByArticle: (articleId: string) =>
    adminFetch<StructuredOutput>(`/admin/outputs/by-article/${encodeURIComponent(articleId)}`),
};
