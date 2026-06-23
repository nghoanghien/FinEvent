"use client";

import axios from "axios";
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
} from "../types";

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

// ======= Axios Client Instance =======
export const http = axios.create({
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Attach Base URL and dynamic Admin API Key on every request
http.interceptors.request.use(
  (config) => {
    const runtimeConfig = getStoredConfig();
    config.baseURL = runtimeConfig.baseUrl.replace(/\/$/, "");
    if (runtimeConfig.adminApiKey) {
      config.headers["X-Admin-API-Key"] = runtimeConfig.adminApiKey;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response Interceptor: Unwrap response data & Parse errors to AdminApiError
http.interceptors.response.use(
  (response) => {
    return response.data;
  },
  async (error) => {
    throw await parseAxiosError(error);
  },
);

// ======= Fetch Wrappers using Axios =======
export async function adminFetch<T>(
  path: string,
  options: RequestInit & { query?: Record<string, QueryValue> } = {},
): Promise<T> {
  const { query, headers, body, method = "GET", signal } = options;

  let data: any = body;
  if (typeof body === "string") {
    try {
      data = JSON.parse(body);
    } catch {
      // not a JSON string, keep as is
    }
  }

  const response = await http.request<T>({
    url: path,
    method,
    data,
    params: query,
    headers: headers as any,
    signal: signal as any,
  });

  return response as any;
}

export async function adminFetchText(path: string, query?: Record<string, QueryValue>): Promise<string> {
  const response = await http.request<string>({
    url: path,
    method: "GET",
    params: query,
    responseType: "text",
    headers: { Accept: "text/plain, text/markdown, application/json" },
  });
  return response as any;
}

export async function adminFetchBlob(path: string, query?: Record<string, QueryValue>): Promise<Blob> {
  const response = await http.request<Blob>({
    url: path,
    method: "GET",
    params: query,
    responseType: "blob",
    headers: { Accept: "*/*" },
  });
  return response as any;
}

// ======= Helper functions for Error Parsing =======

async function parseAxiosError(error: any): Promise<AdminApiError> {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status || 500;
    const statusText = error.response?.statusText || error.message || "Unknown Network Error";
    const contentType = error.response?.headers["content-type"] || "";
    let data = error.response?.data;

    // Handle Blob error response
    if (data instanceof Blob) {
      try {
        const text = await data.text();
        try {
          data = JSON.parse(text);
        } catch {
          data = text;
        }
      } catch {
        // ignore
      }
    }

    let isHtml = false;
    let payload = data;

    if (typeof contentType === "string" && contentType.includes("text/html") && typeof data === "string") {
      isHtml = true;
    } else if (typeof data === "string" && data.trim().startsWith("<")) {
      isHtml = true;
    }

    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      const record = payload as Record<string, unknown>;
      let message = "";

      if (record.message) {
        message = String(record.message);
      } else if (record.detail !== undefined && record.detail !== null) {
        message = formatDetail(record.detail);
      } else {
        message = statusText;
      }

      return new AdminApiError(
        message || statusText || `Request failed with status ${status}`,
        status,
        typeof record.error_code === "string" ? record.error_code : undefined,
        record.details,
      );
    }

    if (typeof payload === "string") {
      const message = isHtml ? cleanHtmlMessage(payload, statusText) : payload.trim();
      return new AdminApiError(message || statusText || `Request failed with status ${status}`, status);
    }

    return new AdminApiError(statusText || `Request failed with status ${status}`, status);
  }

  return new AdminApiError(error instanceof Error ? error.message : String(error), 500);
}

export async function toApiError(response: Response) {
  let payload: unknown = null;
  let isHtml = false;

  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    try {
      payload = await response.json();
    } catch {
      payload = await response.text().catch(() => null);
    }
  } else {
    payload = await response.text().catch(() => null);
    if (typeof payload === "string" && (payload.trim().startsWith("<") || contentType.includes("text/html"))) {
      isHtml = true;
    }
  }

  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const record = payload as Record<string, unknown>;
    let message = "";

    if (record.message) {
      message = String(record.message);
    } else if (record.detail !== undefined && record.detail !== null) {
      message = formatDetail(record.detail);
    } else {
      message = response.statusText;
    }

    return new AdminApiError(
      message || response.statusText || `Request failed with status ${response.status}`,
      response.status,
      typeof record.error_code === "string" ? record.error_code : undefined,
      record.details,
    );
  }

  if (typeof payload === "string") {
    const message = isHtml ? cleanHtmlMessage(payload, response.statusText) : payload.trim();
    return new AdminApiError(message || response.statusText || `Request failed with status ${response.status}`, response.status);
  }

  return new AdminApiError(response.statusText || `Request failed with status ${response.status}`, response.status);
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object") {
          const loc = (item as Record<string, unknown>).loc;
          const msg = (item as Record<string, unknown>).msg;
          if (Array.isArray(loc) && msg) {
            const fieldPath = loc.filter((part) => part !== "body" && part !== "query" && part !== "path").join(".");
            return fieldPath ? `${fieldPath}: ${msg}` : String(msg);
          }
          if (msg) {
            return String(msg);
          }
          return JSON.stringify(item);
        }
        return String(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

function cleanHtmlMessage(html: string, statusText: string): string {
  try {
    const titleMatch = html.match(/<title>(.*?)<\/title>/i);
    if (titleMatch && titleMatch[1]) {
      return titleMatch[1].trim();
    }
    const h1Match = html.match(/<h1>(.*?)<\/h1>/i);
    if (h1Match && h1Match[1]) {
      return h1Match[1].trim();
    }
  } catch {
    // Ignore matching errors
  }
  if (html.length > 200 || /<[a-z][\s\S]*>/i.test(html)) {
    return statusText || "Yêu cầu gặp sự cố phía máy chủ.";
  }
  return html.trim();
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
