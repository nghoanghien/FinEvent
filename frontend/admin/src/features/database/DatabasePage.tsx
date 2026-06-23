"use client";

import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { adminApi } from "@/lib/admin-api";
import { compactJson } from "@/lib/format";
import type { DbEntity } from "@/lib/types";

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

  const rows = useQuery({
    queryKey: ["db", entity, query, offset],
    queryFn: () => adminApi.dbList(entity, { query, limit: 50, offset }),
  });
  const detail = useQuery({
    queryKey: ["db-detail", entity, selectedId],
    queryFn: () => adminApi.dbDetail(entity, selectedId || ""),
    enabled: Boolean(selectedId),
  });

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
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-brand-700">Database browser</p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">Xem dữ liệu PostgreSQL qua allowlist</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Frontend không nhận tên bảng trực tiếp. Backend map entity sang bảng an toàn và bỏ vector lớn khỏi detail response.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[300px_1fr]">
        <aside className="panel p-4">
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
                className={`focus-ring w-full rounded-lg border p-3 text-left ${
                  entity === item.id
                    ? "border-slate-950 bg-slate-950 text-white"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                <p className="text-sm font-semibold">{item.label}</p>
                <p className={`mt-1 text-xs ${entity === item.id ? "text-slate-300" : "text-slate-500"}`}>
                  {item.description}
                </p>
              </button>
            ))}
          </div>
        </aside>

        <section className="space-y-4">
          <div className="panel p-4">
            <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
              <div>
                <h3 className="text-sm font-semibold text-slate-950">{entities.find((item) => item.id === entity)?.label}</h3>
                <p className="mt-1 text-sm text-slate-500">Total: {rows.data?.total ?? "-"}</p>
              </div>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setOffset(0);
                  }}
                  placeholder="Tìm article_id, ticker, title..."
                  className="focus-ring h-9 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm md:w-80"
                />
              </div>
            </div>
          </div>

          {rows.isLoading ? <LoadingBlock /> : null}
          {rows.error ? <ErrorBlock error={rows.error} onRetry={() => rows.refetch()} /> : null}
          {rows.data ? (
            <>
              <DataTable
                rows={rows.data.items as Record<string, unknown>[]}
                columns={columns}
                onRowClick={(row) => setSelectedId(String(row[idKey] || ""))}
                emptyText="Không có record phù hợp."
              />
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - 50))}
                  className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-50"
                >
                  Previous
                </button>
                <p className="text-sm text-slate-500">
                  {offset + 1}-{Math.min(offset + 50, rows.data.total)} / {rows.data.total}
                </p>
                <button
                  type="button"
                  disabled={offset + 50 >= rows.data.total}
                  onClick={() => setOffset(offset + 50)}
                  className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </>
          ) : null}
        </section>
      </div>

      {selectedId ? (
        <section className="panel p-5">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Record detail</h3>
              <p className="mt-1 font-mono text-xs text-slate-500">{entity}/{selectedId}</p>
            </div>
            <button className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-sm" onClick={() => setSelectedId(null)}>
              Đóng
            </button>
          </div>
          {detail.isLoading ? <LoadingBlock /> : null}
          {detail.error ? <ErrorBlock error={detail.error} /> : null}
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
