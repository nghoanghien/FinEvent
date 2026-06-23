"use client";

import { getStoredConfig } from "./config";
import { toApiError } from "./http";
import type { LogEvent } from "../types";

type StreamHandlers = {
  onEvent: (event: LogEvent) => void;
  onOpen?: () => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
};

/**
 * Stream real-time logs for a specific run via Server-Sent Events (SSE).
 * Uses native fetch (not Axios) because Axios does not support ReadableStream.
 */
export async function streamRunLogs(runId: string, handlers: StreamHandlers) {
  const config = getStoredConfig();
  const baseUrl = config.baseUrl.replace(/\/$/, "");
  const url = `${baseUrl}/admin/runs/${encodeURIComponent(runId)}/logs/stream`;

  const headers: Record<string, string> = {
    Accept: "text/event-stream",
  };
  if (config.adminApiKey) {
    headers["X-Admin-API-Key"] = config.adminApiKey;
  }

  const response = await fetch(url, {
    headers,
    cache: "no-store",
    signal: handlers.signal,
  });
  if (!response.ok || !response.body) {
    throw await toApiError(response);
  }
  handlers.onOpen?.();

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const event of events) {
      const dataLine = event
        .split("\n")
        .find((line) => line.startsWith("data:"));
      if (!dataLine) continue;
      const payload = dataLine.replace(/^data:\s?/, "").trim();
      if (!payload || payload === "[DONE]") continue;
      try {
        handlers.onEvent(JSON.parse(payload) as LogEvent);
      } catch (error) {
        handlers.onError?.(error instanceof Error ? error : new Error(String(error)));
      }
    }
  }
}
