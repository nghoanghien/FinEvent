import type { RunStatus } from "../types";

export function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}

export function formatBytes(value?: number | null) {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function compactJson(value: unknown, maxLength = 90) {
  if (value === null || value === undefined) return "-";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  if (!text) return "-";
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

export function statusTone(status?: RunStatus | string) {
  switch (status) {
    case "success":
    case "ok":
    case "configured":
      return "success";
    case "running":
      return "info";
    case "queued":
      return "neutral";
    case "failed":
    case "error":
    case "missing":
    case "unconfigured":
      return "danger";
    case "canceled":
    case "interrupted":
      return "warning";
    default:
      return "neutral";
  }
}

export function eventCount(output: Record<string, unknown> | undefined) {
  const events = output?.events;
  return Array.isArray(events) ? events.length : 0;
}

export function getStructuredPrediction(payload: {
  prediction?: Record<string, unknown>;
  output?: Record<string, unknown>;
}) {
  return payload.prediction || payload.output || {};
}
