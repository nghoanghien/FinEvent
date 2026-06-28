"use client";

import { Boxes, RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock, EmptyBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { compactJson, eventCount, formatDateTime, getStructuredPrediction } from "@/shared/utils/format";
import type { StructuredOutput } from "@/shared/types";
import { useOutputByArticle, useOutputDetail, useOutputsList } from "./hooks/useOutputs";

export function OutputsPage() {
  const [articleId, setArticleId] = useState("");
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const outputs = useOutputsList(articleId);
  const selected = useOutputDetail(selectedRunId);
  const articleOutput = useOutputByArticle(articleId, Boolean(articleId && !selectedRunId));
  const detail = selected.data || articleOutput.data;

  async function refresh() {
    await Promise.all([outputs.refetch(), selected.refetch(), articleOutput.refetch()]);
  }

  return (
    <div className="finevent-page space-y-8">
      <PageHeader
        eyebrow="Structured outputs"
        title="EVENT OUTPUTS"
        icon={Boxes}
        description="Kiểm tra bảng sự kiện model sinh ra: event table, evidence, validation issues, hallucination metrics và node traces."
        actions={
          <button type="button" onClick={refresh} className="finevent-secondary-button">
            <RefreshCw className={`h-4 w-4 ${outputs.isFetching || selected.isFetching || articleOutput.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <div className="panel p-5">
        <div className="relative max-w-xl">
          <Search className="pointer-events-none absolute left-4 top-3.5 h-4 w-4 text-gray-400" />
          <input
            value={articleId}
            onChange={(event) => {
              setArticleId(event.target.value.trim());
              setSelectedRunId(null);
            }}
            placeholder="Tìm theo article_id"
            className="focus-ring h-12 w-full rounded-full border border-gray-100 bg-gray-100 pl-11 pr-4 text-sm font-medium text-gray-700 placeholder:text-gray-400"
          />
        </div>
      </div>

      <section className="grid gap-5 xl:grid-cols-[440px_1fr]">
        <aside className="panel p-5">
          <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Extraction runs</h3>
          <p className="mt-1 text-sm font-medium text-gray-400">Nguồn: {outputs.data?.source || "auto"}</p>
          <div className="mt-5">
            {outputs.isLoading ? <LoadingBlock label="Đang tải output list..." /> : null}
            {outputs.error ? <ErrorBlock error={outputs.error} onRetry={() => outputs.refetch()} /> : null}
            {outputs.data?.items.length ? (
              <div className="space-y-2">
                {outputs.data.items.map((item) => (
                  <button
                    key={item.run_id}
                    type="button"
                    onClick={() => setSelectedRunId(item.run_id)}
                    className={`focus-ring w-full rounded-[24px] border p-4 text-left transition-all duration-300 ${
                      selectedRunId === item.run_id
                        ? "border-primary/40 bg-lime-50 text-gray-950 shadow-[inset_0_0_20px_12px_rgba(255,255,255,0.8)]"
                        : "border-gray-100 bg-white hover:-translate-y-0.5 hover:shadow-finevent"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-mono text-xs font-black">{item.run_id}</p>
                        <p className="mt-1 truncate text-xs font-medium text-gray-500">{item.article_id || "-"}</p>
                      </div>
                      <StatusBadge value={item.document_label || "-"} />
                    </div>
                    <p className="mt-2 text-xs font-medium text-gray-500">{formatDateTime(item.created_at)}</p>
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
          {selected.error ? <ErrorBlock error={selected.error} onRetry={() => selected.refetch()} /> : null}
          {articleOutput.error && articleId && !selectedRunId ? <ErrorBlock error={articleOutput.error} onRetry={() => articleOutput.refetch()} /> : null}
          {detail ? (
            <OutputDetail output={detail} />
          ) : !selected.isLoading && !articleOutput.isLoading ? (
            <EmptyBlock title="Chọn một output để xem chi tiết" />
          ) : null}
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
    <div className="space-y-5">
      <section className="grid gap-4 md:grid-cols-4">
        <Info label="Source" value={output.source} />
        <Info label="Run" value={output.run_id || String(output.run?.run_id || "-")} />
        <Info label="Article" value={output.article_id || String(output.run?.article_id || "-")} />
        <Info label="Events" value={String(eventCount(prediction))} />
      </section>

      <section className="panel p-8">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Event table</h3>
            <p className="mt-1 text-sm font-medium text-gray-400">Bảng output chuẩn hóa từ bài báo.</p>
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
        <section className="panel p-8">
          <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Evidence spans</h3>
          <div className="mt-5 space-y-3">
            {events.map((event, index) => (
              <div key={String(event.event_id || index)} className="rounded-[24px] border border-gray-100 bg-gray-50 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge value={String(event.event_type || "-")} />
                  <span className="font-mono text-xs font-medium text-gray-500">{String(event.event_id || `event_${index + 1}`)}</span>
                </div>
                <p className="mt-3 text-sm font-medium text-gray-700">{String(event.evidence_span || "No evidence span")}</p>
                <p className="mt-3 text-xs font-medium text-gray-500">{compactJson(event.event_arguments, 220)}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="panel p-8">
          <h3 className="mb-4 font-anton text-2xl font-black uppercase text-gray-900">Verification report</h3>
          <JsonPanel value={output.verification_report || {}} />
        </div>
        <div className="panel p-8">
          <h3 className="mb-4 font-anton text-2xl font-black uppercase text-gray-900">Hallucination metrics</h3>
          <JsonPanel value={output.hallucination_metrics || {}} />
        </div>
      </section>

      <section className="panel p-8">
        <h3 className="mb-4 font-anton text-2xl font-black uppercase text-gray-900">Raw output</h3>
        <JsonPanel value={output} />
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-5">
      <p className="text-xs font-black uppercase text-gray-400">{label}</p>
      <p className="mt-2 truncate text-sm font-bold text-gray-950">{value || "-"}</p>
    </div>
  );
}
