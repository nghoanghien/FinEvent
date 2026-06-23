"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock, EmptyBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { adminApi } from "@/lib/admin-api";
import { compactJson, eventCount, formatDateTime, getStructuredPrediction } from "@/lib/format";
import type { StructuredOutput } from "@/lib/types";

export function OutputsPage() {
  const [articleId, setArticleId] = useState("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const outputs = useQuery({
    queryKey: ["outputs", articleId],
    queryFn: () => adminApi.outputs({ article_id: articleId || undefined, limit: 50 }),
  });

  const selected = useQuery({
    queryKey: ["output-detail", selectedRunId],
    queryFn: () => adminApi.output(selectedRunId || ""),
    enabled: Boolean(selectedRunId),
  });

  const articleOutput = useQuery({
    queryKey: ["output-by-article", articleId],
    queryFn: () => adminApi.outputByArticle(articleId),
    enabled: Boolean(articleId && !selectedRunId),
  });

  const detail = selected.data || articleOutput.data;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-brand-700">Structured outputs</p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">Kiểm tra bảng sự kiện model sinh ra</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Màn hình này ưu tiên output có cấu trúc: event table, evidence, validation issues, hallucination metrics và node traces.
        </p>
      </div>

      <div className="panel p-4">
        <div className="relative max-w-xl">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            value={articleId}
            onChange={(event) => {
              setArticleId(event.target.value.trim());
              setSelectedRunId(null);
            }}
            placeholder="Tìm theo article_id"
            className="focus-ring h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm"
          />
        </div>
      </div>

      <section className="grid gap-4 xl:grid-cols-[420px_1fr]">
        <aside className="panel p-4">
          <h3 className="text-sm font-semibold text-slate-950">Extraction runs</h3>
          <p className="mt-1 text-sm text-slate-500">Nguồn: {outputs.data?.source || "auto"}</p>
          <div className="mt-4">
            {outputs.isLoading ? <LoadingBlock label="Đang tải output list..." /> : null}
            {outputs.error ? <ErrorBlock error={outputs.error} /> : null}
            {outputs.data?.items.length ? (
              <div className="space-y-2">
                {outputs.data.items.map((item) => (
                  <button
                    key={item.run_id}
                    type="button"
                    onClick={() => setSelectedRunId(item.run_id)}
                    className={`focus-ring w-full rounded-lg border p-3 text-left ${
                      selectedRunId === item.run_id ? "border-slate-950 bg-slate-950 text-white" : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-mono text-xs font-semibold">{item.run_id}</p>
                        <p className={`mt-1 truncate text-xs ${selectedRunId === item.run_id ? "text-slate-300" : "text-slate-500"}`}>
                          {item.article_id || "-"}
                        </p>
                      </div>
                      <StatusBadge value={item.document_label || "-"} />
                    </div>
                    <p className={`mt-2 text-xs ${selectedRunId === item.run_id ? "text-slate-300" : "text-slate-500"}`}>
                      {formatDateTime(item.created_at)}
                    </p>
                  </button>
                ))}
              </div>
            ) : null}
            {outputs.data && !outputs.data.items.length ? (
              <EmptyBlock title="Chưa có output" description="Hãy chạy student batch extraction hoặc nhập article_id khác." />
            ) : null}
          </div>
        </aside>

        <main>
          {selected.isLoading || articleOutput.isLoading ? <LoadingBlock label="Đang tải output detail..." /> : null}
          {selected.error ? <ErrorBlock error={selected.error} /> : null}
          {articleOutput.error && articleId && !selectedRunId ? <ErrorBlock error={articleOutput.error} /> : null}
          {detail ? <OutputDetail output={detail} /> : !selected.isLoading && !articleOutput.isLoading ? <EmptyBlock title="Chọn một output để xem chi tiết" /> : null}
        </main>
      </section>
    </div>
  );
}

function OutputDetail({ output }: { output: StructuredOutput }) {
  const prediction = getStructuredPrediction(output);
  const events = useMemo(() => {
    const raw = prediction.events;
    return Array.isArray(raw) ? (raw as Record<string, unknown>[]) : [];
  }, [prediction]);

  return (
    <div className="space-y-4">
      <section className="grid gap-4 md:grid-cols-4">
        <Info label="Source" value={output.source} />
        <Info label="Run" value={output.run_id || String(output.run?.run_id || "-")} />
        <Info label="Article" value={output.article_id || String(output.run?.article_id || "-")} />
        <Info label="Events" value={String(eventCount(prediction))} />
      </section>

      <section className="panel p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">Event table</h3>
            <p className="mt-1 text-sm text-slate-500">Bảng output chuẩn hóa từ bài báo.</p>
          </div>
          <StatusBadge value={String(prediction.document_label || output.run?.document_label || "-")} />
        </div>
        <DataTable
          rows={events}
          columns={[
            { key: "ticker", label: "Ticker" },
            { key: "company_name", label: "Company" },
            { key: "event_type", label: "Type", render: (row) => <StatusBadge value={String(row.event_type || "-")} /> },
            { key: "event_subtype", label: "Subtype" },
            { key: "impact_sentiment", label: "Impact", render: (row) => <StatusBadge value={String(row.impact_sentiment || "-")} /> },
            { key: "confidence", label: "Conf." },
          ]}
          emptyText="Output không có event."
        />
      </section>

      {events.length ? (
        <section className="panel p-5">
          <h3 className="text-sm font-semibold text-slate-950">Evidence spans</h3>
          <div className="mt-4 space-y-3">
            {events.map((event, index) => (
              <div key={String(event.event_id || index)} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge value={String(event.event_type || "-")} />
                  <span className="font-mono text-xs text-slate-500">{String(event.event_id || `event_${index + 1}`)}</span>
                </div>
                <p className="mt-2 text-sm text-slate-700">{String(event.evidence_span || "No evidence span")}</p>
                <p className="mt-2 text-xs text-slate-500">{compactJson(event.event_arguments, 220)}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="panel p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-950">Verification report</h3>
          <JsonPanel value={output.verification_report || {}} />
        </div>
        <div className="panel p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-950">Hallucination metrics</h3>
          <JsonPanel value={output.hallucination_metrics || {}} />
        </div>
      </section>

      <section className="panel p-5">
        <h3 className="mb-3 text-sm font-semibold text-slate-950">Raw output</h3>
        <JsonPanel value={output} />
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 truncate text-sm font-semibold text-slate-950">{value || "-"}</p>
    </div>
  );
}
