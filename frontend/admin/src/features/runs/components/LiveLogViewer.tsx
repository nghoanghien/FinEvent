"use client";

import { useQuery } from "@tanstack/react-query";
import { Pause, Play, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { adminApi } from "@/shared/utils/api";
import { formatDateTime } from "@/shared/utils/format";
import { streamRunLogs } from "@/shared/utils/stream";
import type { LogEvent } from "@/shared/types";

export function LiveLogViewer({ runId, enabled }: { runId: string; enabled: boolean }) {
  const [events, setEvents] = useState<LogEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [query, setQuery] = useState("");
  const [streamError, setStreamError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const history = useQuery({
    queryKey: ["run-logs", runId],
    queryFn: () => adminApi.logs(runId, { limit: 300 }),
  });

  useEffect(() => {
    if (history.data?.items) {
      setEvents(history.data.items);
    }
  }, [history.data]);

  useEffect(() => {
    if (!enabled || paused) return;
    const controller = new AbortController();
    streamRunLogs(runId, {
      signal: controller.signal,
      onEvent: (event) => {
        setEvents((current) => {
          if (current.some((item) => item.timestamp === event.timestamp && item.message === event.message)) {
            return current;
          }
          return [...current.slice(-599), event];
        });
      },
      onError: (error) => setStreamError(error.message),
    }).catch((error) => {
      if (!controller.signal.aborted) {
        setStreamError(error instanceof Error ? error.message : String(error));
      }
    });
    return () => controller.abort();
  }, [enabled, paused, runId]);

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ block: "end" });
  }, [events, paused]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return events;
    return events.filter((event) =>
      `${event.level} ${event.stream} ${event.step_id} ${event.message}`.toLowerCase().includes(needle),
    );
  }, [events, query]);

  return (
    <section className="panel p-8">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <div className="h-6 w-1.5 rounded-full bg-primary" />
            <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Live logs</h3>
          </div>
          <p className="pl-3.5 text-sm font-medium text-gray-400">
            Streaming log giống notebook/collab, có thể pause và lọc theo nội dung.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-3.5 h-4 w-4 text-gray-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm trong log"
              className="focus-ring h-12 w-60 rounded-full border border-gray-100 bg-gray-100 pl-11 pr-4 text-sm font-medium text-gray-700 placeholder:text-gray-400"
            />
          </div>
          <button type="button" onClick={() => setPaused((value) => !value)} className="finevent-secondary-button">
            {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>
      {history.isLoading ? (
        <div className="mt-5">
          <LoadingBlock label="Đang tải log history..." />
        </div>
      ) : null}
      {history.error ? (
        <div className="mt-5">
          <ErrorBlock error={history.error} />
        </div>
      ) : null}
      {streamError ? (
        <div className="mt-5 rounded-2xl border border-warning/30 bg-orange-50 p-3 text-sm font-semibold text-orange-800">
          Stream warning: {streamError}
        </div>
      ) : null}
      <div className="mt-5 max-h-[520px] overflow-auto rounded-[24px] border border-gray-900 bg-gray-950 p-4 font-mono text-xs leading-6 text-gray-200">
        {filtered.length ? (
          filtered.map((event, index) => (
            <div key={`${event.timestamp}-${index}`} className="grid gap-2 border-b border-white/5 py-1.5 md:grid-cols-[170px_78px_120px_1fr]">
              <span className="text-gray-500">{formatDateTime(event.timestamp)}</span>
              <StatusBadge value={event.level} className="h-5 border-gray-700 bg-gray-900 text-gray-200" />
              <span className="truncate text-lime-300">{event.step_id || event.stream}</span>
              <span className="whitespace-pre-wrap text-gray-100">{event.message}</span>
            </div>
          ))
        ) : (
          <p className="p-4 text-gray-500">Chưa có log phù hợp.</p>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
