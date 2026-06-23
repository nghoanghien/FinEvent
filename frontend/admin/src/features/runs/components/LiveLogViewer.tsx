"use client";

import { useQuery } from "@tanstack/react-query";
import { Pause, Play, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { adminApi } from "@/lib/admin-api";
import { formatDateTime } from "@/lib/format";
import { streamRunLogs } from "@/lib/stream";
import type { LogEvent } from "@/lib/types";

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
    <section className="panel p-5">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Live logs</h3>
          <p className="mt-1 text-sm text-slate-500">
            Fetch streaming được dùng để gửi được header auth `X-Admin-API-Key`.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm trong log"
              className="focus-ring h-9 w-56 rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm"
            />
          </div>
          <button
            type="button"
            onClick={() => setPaused((value) => !value)}
            className="focus-ring inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>
      {history.isLoading ? <div className="mt-4"><LoadingBlock label="Đang tải log history..." /></div> : null}
      {history.error ? <div className="mt-4"><ErrorBlock error={history.error} /></div> : null}
      {streamError ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Stream warning: {streamError}
        </div>
      ) : null}
      <div className="mt-4 max-h-[520px] overflow-auto rounded-lg border border-slate-900 bg-slate-950 p-3 font-mono text-xs leading-6 text-slate-200">
        {filtered.length ? (
          filtered.map((event, index) => (
            <div key={`${event.timestamp}-${index}`} className="grid gap-2 border-b border-white/5 py-1.5 md:grid-cols-[170px_78px_120px_1fr]">
              <span className="text-slate-500">{formatDateTime(event.timestamp)}</span>
              <StatusBadge value={event.level} className="h-5 border-slate-700 bg-slate-900 text-slate-200" />
              <span className="truncate text-sky-300">{event.step_id || event.stream}</span>
              <span className="whitespace-pre-wrap text-slate-100">{event.message}</span>
            </div>
          ))
        ) : (
          <p className="p-4 text-slate-500">Chưa có log phù hợp.</p>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
