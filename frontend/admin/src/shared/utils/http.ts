"use client";

import axios from "axios";
import { getStoredConfig } from "./config";

// ======= Custom Error Class =======
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

// ======= Axios Client Instance =======
export const http = axios.create({
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
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
    return response.data ?? response;
  },
  async (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const statusText = error.response?.statusText || error.message || "Unknown Error";
      let data = error.response?.data;

      // Handle Blob error response (e.g. report download failures)
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

      // Detect HTML error pages (e.g. Nginx 502/504)
      const contentType = error.response?.headers?.["content-type"] || "";
      const isHtml =
        (typeof contentType === "string" && contentType.includes("text/html") && typeof data === "string") ||
        (typeof data === "string" && data.trim().startsWith("<"));

      // Parse structured JSON error (FastAPI format)
      if (data && typeof data === "object" && !Array.isArray(data)) {
        const record = data as Record<string, unknown>;
        let message = "";

        if (record.message) {
          message = String(record.message);
        } else if (record.detail !== undefined && record.detail !== null) {
          message = formatDetail(record.detail);
        } else {
          message = statusText;
        }

        return Promise.reject(
          new AdminApiError(
            message || statusText,
            status,
            typeof record.error_code === "string" ? record.error_code : undefined,
            record.details,
          ),
        );
      }

      // Parse string/HTML error
      if (typeof data === "string") {
        const message = isHtml ? cleanHtmlMessage(data, statusText) : data.trim();
        return Promise.reject(new AdminApiError(message || statusText, status));
      }

      return Promise.reject(new AdminApiError(statusText, status));
    }

    // Non-Axios error fallback
    return Promise.reject(
      new AdminApiError(error instanceof Error ? error.message : String(error), 500),
    );
  },
);

// ======= toApiError for native fetch (used by SSE stream) =======
export async function toApiError(response: Response): Promise<AdminApiError> {
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
    return new AdminApiError(message || response.statusText, response.status);
  }

  return new AdminApiError(response.statusText || `Request failed with status ${response.status}`, response.status);
}

// ======= Error Detail Formatters =======

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
            const fieldPath = loc
              .filter((part) => part !== "body" && part !== "query" && part !== "path")
              .join(".");
            return fieldPath ? `${fieldPath}: ${msg}` : String(msg);
          }
          if (msg) return String(msg);
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
    if (titleMatch?.[1]) return titleMatch[1].trim();
    const h1Match = html.match(/<h1>(.*?)<\/h1>/i);
    if (h1Match?.[1]) return h1Match[1].trim();
  } catch {
    // Ignore
  }
  if (html.length > 200 || /<[a-z][\s\S]*>/i.test(html)) {
    return statusText || "Yêu cầu gặp sự cố phía máy chủ.";
  }
  return html.trim();
}
