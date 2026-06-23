"use client";

import { adminHeaders, buildUrl } from "./admin-api";
import type { LogEvent } from "./types";

type StreamHandlers = {
  onEvent: (event: LogEvent) => void;
  onOpen?: () => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
};

export async function streamRunLogs(runId: string, handlers: StreamHandlers) {
  const response = await fetch(buildUrl(`/admin/runs/${encodeURIComponent(runId)}/logs/stream`), {
    headers: adminHeaders({ Accept: "text/event-stream" }),
    cache: "no-store",
    signal: handlers.signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Log stream failed with HTTP ${response.status}.`);
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
