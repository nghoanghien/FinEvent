"use client";

import { Database, RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { compactJson } from "@/lib/format";
import type { DbEntity } from "@/lib/types";
import { useDatabaseDetail, useDatabaseRows } from "./hooks/useDatabaseBrowser";

const entities: { id: DbEntity; label: string; description: string }[] = [
  { id: "articles", label: "Articles", description: "Bài báo đã ingest" },
  { id: "chunks", label: "Chunks", description: "Chunk semantic/structure-aware" },
  { id: "embeddings", label: "Embeddings", description: "Vector embedding metadata" },
  { id: "gold-labels", label: "Gold labels", description: "Document labels từ teacher" },
  { id: "gold-events", label: "Gold events", description: "Event rows đã chuẩn hóa" },
  { id: "patterns", label: "Patterns", description: "Few-shot/event pattern library" },
  { id: "extraction-runs", label: "Extraction runs", description: "Student outputs" },
  { id: "node-traces", label: "Node traces", description: "Trace từng node workflow" },
  { id: "tickers", label: "Tickers", description: "Ticker dictionary" },
];

export function DatabasePage() {
  const [entity, setEntity] = useState<DbEntity>("articles");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const rows = useDatabaseRows(entity, query, offset, 50);
  const detail = useDatabaseDetail(entity, selectedId);

  const columns = useMemo<Column<Record<string, unknown>>[]>(() => {
    const sample = rows.data?.items?.[0];
    const keys = sample ? Object.keys(sample).slice(0, 8) : defaultColumns(entity);
    return keys.map((key) => ({
      key,
      label: key,
      render: (row) => renderCell(key, row[key]),
    }));
  }, [entity, rows.data?.items]);

  const idKey = idColumnForEntity(entity);

  return (
    <div className="eatzy-page space-y-8">
      <PageHeader
        eyebrow="Database browser"
        title="DATA BROWSER"
        icon={Database}
        description="Xem dữ liệu PostgreSQL qua allowlist an toàn. Frontend không nhận tên bảng trực tiếp và backend loại bỏ vector lớn khỏi detail response."
        actions={
          <button type="button" onClick={() => rows.refetch()} className="eatzy-secondary-button">
            <RefreshCw className={`h-4 w-4 ${rows.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[320px_1fr]">
        <aside className="panel p-5">
          <div className="space-y-2">
            {entities.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setEntity(item.id);
                  setSelectedId(null);
                  setOffset(0);
                }}
                className={`focus-ring w-full rounded-[22px] border p-4 text-left transition-all duration-300 ${
                  entity === item.id
                    ? "border-primary/40 bg-lime-50 text-gray-950 shadow-[inset_0_0_20px_12px_rgba(255,255,255,0.8)]"
                    : "border-gray-100 bg-white text-gray-700 hover:-translate-y-0.5 hover:shadow-eatzy"
                }`}
              >
                <p className="text-sm font-black">{item.label}</p>
                <p className="mt-1 text-xs font-medium text-gray-500">{item.description}</p>
              </button>
            ))}
          </div>
        </aside>

        <section className="space-y-5">
          <div className="panel p-5">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
              <div>
                <h3 className="font-anton text-2xl font-black uppercase text-gray-900">{entities.find((item) => item.id === entity)?.label}</h3>
                <p className="mt-1 text-sm font-medium text-gray-400">Total: {rows.data?.total ?? "-"}</p>
              </div>
              <div className="relative">
                <Search className="pointer-events-none absolute left-4 top-3.5 h-4 w-4 text-gray-400" />
                <input
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setOffset(0);
                  }}
                  placeholder="Tìm article_id, ticker, title..."
                  className="focus-ring h-12 w-full rounded-full border border-gray-100 bg-gray-100 pl-11 pr-4 text-sm font-medium text-gray-700 placeholder:text-gray-400 md:w-96"
                />
              </div>
            </div>
          </div>

          {rows.error ? <ErrorBlock error={rows.error} onRetry={() => rows.refetch()} /> : null}
          <DataTable
            rows={(rows.data?.items || []) as Record<string, unknown>[]}
            columns={columns}
            isLoading={rows.isLoading}
            onRowClick={(row) => setSelectedId(String(row[idKey] || ""))}
            emptyText="Không có record phù hợp."
          />
          {rows.data ? (
            <div className="flex items-center justify-between">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 50))}
                className="eatzy-secondary-button disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <p className="text-sm font-medium text-gray-500">
                {offset + 1}-{Math.min(offset + 50, rows.data.total)} / {rows.data.total}
              </p>
              <button
                type="button"
                disabled={offset + 50 >= rows.data.total}
                onClick={() => setOffset(offset + 50)}
                className="eatzy-secondary-button disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          ) : null}
        </section>
      </div>

      {selectedId ? (
        <section className="panel p-8">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Record detail</h3>
              <p className="mt-1 font-mono text-xs font-medium text-gray-500">{entity}/{selectedId}</p>
            </div>
            <button className="eatzy-secondary-button" onClick={() => setSelectedId(null)}>
              Đóng
            </button>
          </div>
          {detail.isLoading ? <LoadingBlock label="Đang tải record detail..." /> : null}
          {detail.error ? <ErrorBlock error={detail.error} onRetry={() => detail.refetch()} /> : null}
          {detail.data ? <JsonPanel value={detail.data.record} /> : null}
        </section>
      ) : null}
    </div>
  );
}

function renderCell(key: string, value: unknown) {
  if (key.includes("status") || key.includes("label") || key === "impact_sentiment") {
    return <StatusBadge value={String(value || "-")} />;
  }
  return <span className="line-clamp-2">{compactJson(value)}</span>;
}

function idColumnForEntity(entity: DbEntity) {
  const mapping: Record<DbEntity, string> = {
    articles: "article_id",
    chunks: "chunk_id",
    embeddings: "embedding_id",
    "gold-labels": "article_id",
    "gold-events": "event_id",
    patterns: "pattern_id",
    "extraction-runs": "run_id",
    "node-traces": "trace_id",
    tickers: "ticker",
  };
  return mapping[entity];
}

function defaultColumns(entity: DbEntity) {
  return [idColumnForEntity(entity), "article_id", "ticker", "status", "created_at"];
}
