"use client";

import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { useMemo, useState } from "react";
import { BarChart3, FileText, ImageIcon, RefreshCw, Table2 } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock, EmptyBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { SecureArtifactImage } from "@/components/ui/SecureArtifactImage";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { adminApi } from "@/lib/admin-api";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { ReportArtifact } from "@/lib/types";

const kinds = ["all", "markdown", "csv", "jsonl", "image", "svg", "json", "text"];

export function ReportsPage() {
  const [kind, setKind] = useState("all");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const reports = useQuery({
    queryKey: ["reports", kind],
    queryFn: () => adminApi.reports({ kind: kind === "all" ? undefined : kind, limit: 300 }),
  });
  const charts = useQuery({ queryKey: ["charts"], queryFn: adminApi.charts });

  const selectedReport = useMemo(
    () => reports.data?.items.find((item) => item.path === selectedPath) || reports.data?.items[0],
    [reports.data?.items, selectedPath],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-medium text-brand-700">Report center</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">Báo cáo, bảng metric và biểu đồ</h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            Tập trung tất cả artifact trong `reports/`: markdown, CSV, JSONL, SVG/PNG chart và final dashboard.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            reports.refetch();
            charts.refetch();
          }}
          className="focus-ring inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <section className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <aside className="panel p-4">
          <div className="mb-4 flex flex-wrap gap-2">
            {kinds.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setKind(item)}
                className={`focus-ring rounded-full border px-3 py-1.5 text-xs font-medium ${
                  kind === item
                    ? "border-slate-950 bg-slate-950 text-white"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {item}
              </button>
            ))}
          </div>
          {reports.isLoading ? <LoadingBlock label="Đang tải danh sách report..." /> : null}
          {reports.error ? <ErrorBlock error={reports.error} /> : null}
          <div className="space-y-2">
            {(reports.data?.items || []).map((report) => (
              <ReportListItem
                key={report.path}
                report={report}
                active={selectedReport?.path === report.path}
                onClick={() => setSelectedPath(report.path)}
              />
            ))}
          </div>
          {reports.data && !reports.data.items.length ? (
            <EmptyBlock title="Chưa có report" description="Hãy chạy workflow evaluation để sinh artifact." />
          ) : null}
        </aside>

        <div className="space-y-4">
          <ChartOverview charts={charts.data} isLoading={charts.isLoading} error={charts.error} />
          {selectedReport ? <ReportRenderer report={selectedReport} /> : null}
        </div>
      </section>
    </div>
  );
}

function ReportListItem({
  report,
  active,
  onClick,
}: {
  report: ReportArtifact;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = report.kind === "csv" ? Table2 : report.kind === "image" ? ImageIcon : FileText;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`focus-ring w-full rounded-lg border p-3 text-left transition ${
        active ? "border-slate-950 bg-slate-950 text-white" : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${active ? "text-white" : "text-slate-400"}`} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{report.name}</p>
          <p className={`mt-1 truncate text-xs ${active ? "text-slate-300" : "text-slate-500"}`}>{report.path}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge value={report.kind} className={active ? "border-slate-700 bg-slate-900 text-slate-100" : ""} />
            <span className={`text-xs ${active ? "text-slate-300" : "text-slate-500"}`}>{formatBytes(report.size_bytes)}</span>
          </div>
        </div>
      </div>
    </button>
  );
}

function ChartOverview({
  charts,
  isLoading,
  error,
}: {
  charts: Awaited<ReturnType<typeof adminApi.charts>> | undefined;
  isLoading: boolean;
  error: unknown;
}) {
  if (isLoading) return <LoadingBlock label="Đang tải chart index..." />;
  if (error) return <ErrorBlock error={error} />;
  if (!charts) return null;
  return (
    <section className="panel p-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">Chart overview</h3>
          <p className="mt-1 text-sm text-slate-500">Nhóm biểu đồ do pipeline evaluation sinh ra.</p>
        </div>
        <BarChart3 className="h-5 w-5 text-slate-400" />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {charts.groups.map((group) => (
          <div key={group.key} className="rounded-lg border border-slate-200 p-3">
            <p className="text-sm font-semibold text-slate-800">{group.title}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-950">{group.charts.length}</p>
            <p className="text-xs text-slate-500">charts</p>
          </div>
        ))}
      </div>
      {charts.final_dashboard ? (
        <div className="mt-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Final quality dashboard</p>
          <SecureArtifactImage path={charts.final_dashboard} alt="Final quality dashboard" />
        </div>
      ) : null}
    </section>
  );
}

function ReportRenderer({ report }: { report: ReportArtifact }) {
  if (report.kind === "csv") return <CsvReport path={report.path} />;
  if (report.kind === "jsonl") return <JsonlReport path={report.path} />;
  if (report.kind === "image") return <SecureArtifactImage path={report.path} alt={report.name} />;
  return <TextReport report={report} />;
}

function TextReport({ report }: { report: ReportArtifact }) {
  const content = useQuery({
    queryKey: ["report-content", report.path],
    queryFn: () => adminApi.reportContent(report.path),
  });
  if (content.isLoading) return <LoadingBlock label="Đang tải nội dung report..." />;
  if (content.error) return <ErrorBlock error={content.error} />;
  return (
    <section className="panel p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">{report.name}</h3>
          <p className="mt-1 text-xs text-slate-500">{report.path} · {formatDateTime(report.modified_at)}</p>
        </div>
        <StatusBadge value={report.kind} />
      </div>
      {report.kind === "markdown" ? (
        <article className="prose prose-slate max-w-none prose-headings:scroll-mt-20 prose-pre:bg-slate-950 prose-pre:text-slate-100">
          <ReactMarkdown>{content.data || ""}</ReactMarkdown>
        </article>
      ) : (
        <pre className="max-h-[720px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {content.data}
        </pre>
      )}
    </section>
  );
}

function CsvReport({ path }: { path: string }) {
  const table = useQuery({
    queryKey: ["report-table", path],
    queryFn: () => adminApi.reportTable(path, { limit: 200 }),
  });
  if (table.isLoading) return <LoadingBlock label="Đang tải bảng CSV..." />;
  if (table.error) return <ErrorBlock error={table.error} />;
  const columns = (table.data?.columns || []).map((key) => ({ key, label: key }));
  return (
    <section className="panel p-5">
      <h3 className="mb-4 text-sm font-semibold text-slate-950">{path}</h3>
      <DataTable rows={(table.data?.rows || []) as Record<string, unknown>[]} columns={columns} />
    </section>
  );
}

function JsonlReport({ path }: { path: string }) {
  const jsonl = useQuery({
    queryKey: ["report-jsonl", path],
    queryFn: () => adminApi.reportJsonl(path, { limit: 100 }),
  });
  if (jsonl.isLoading) return <LoadingBlock label="Đang tải JSONL..." />;
  if (jsonl.error) return <ErrorBlock error={jsonl.error} />;
  return (
    <section className="panel p-5">
      <h3 className="mb-4 text-sm font-semibold text-slate-950">{path}</h3>
      <JsonPanel value={jsonl.data?.rows || []} />
    </section>
  );
}
