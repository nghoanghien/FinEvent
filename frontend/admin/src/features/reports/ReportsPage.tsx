"use client";

import ReactMarkdown from "react-markdown";
import { useMemo, useState } from "react";
import { BarChart3, FileText, ImageIcon, RefreshCw, Table2 } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock, EmptyBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { SecureArtifactImage } from "@/components/ui/SecureArtifactImage";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatBytes, formatDateTime } from "@/shared/utils/format";
import type { ChartsResponse, ReportArtifact } from "@/shared/types";
import { useCharts, useReportContent, useReportJsonl, useReports, useReportTable } from "./hooks/useReports";

const kinds = ["all", "markdown", "csv", "jsonl", "image", "svg", "json", "text"];

export function ReportsPage() {
  const [kind, setKind] = useState("all");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const reports = useReports(kind, 300);
  const charts = useCharts();

  const selectedReport = useMemo(
    () => reports.data?.items.find((item) => item.path === selectedPath) || reports.data?.items[0],
    [reports.data?.items, selectedPath],
  );

  async function refresh() {
    await Promise.all([reports.refetch(), charts.refetch()]);
  }

  return (
    <div className="finevent-page space-y-8">
      <PageHeader
        eyebrow="Report center"
        title="REPORT VAULT"
        icon={BarChart3}
        description="Tập trung tất cả artifact trong reports/: markdown, CSV, JSONL, SVG/PNG chart và final dashboard."
        actions={
          <button type="button" onClick={refresh} className="finevent-secondary-button">
            <RefreshCw className={`h-4 w-4 ${reports.isFetching || charts.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <section className="grid gap-5 xl:grid-cols-[380px_1fr]">
        <aside className="panel p-5">
          <div className="mb-5 flex flex-wrap gap-2">
            {kinds.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setKind(item)}
                className={`focus-ring rounded-full border px-3 py-1.5 text-xs font-bold transition ${
                  kind === item
                    ? "border-primary/40 bg-primary text-gray-950 shadow-lg shadow-primary/20"
                    : "border-gray-100 bg-gray-50 text-gray-600 hover:bg-white hover:shadow-sm"
                }`}
              >
                {item}
              </button>
            ))}
          </div>
          {reports.isLoading ? <LoadingBlock label="Đang tải danh sách report..." /> : null}
          {reports.error ? <ErrorBlock error={reports.error} onRetry={() => reports.refetch()} /> : null}
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

        <div className="space-y-5">
          <ChartOverview charts={charts.data} isLoading={charts.isLoading} error={charts.error} onRetry={() => charts.refetch()} />
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
      className={`focus-ring w-full rounded-[24px] border p-4 text-left transition-all duration-300 ${
        active
          ? "border-primary/40 bg-lime-50 text-gray-950 shadow-[inset_0_0_24px_16px_rgba(255,255,255,0.8)]"
          : "border-gray-100 bg-white hover:-translate-y-0.5 hover:shadow-finevent"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl ${active ? "bg-white text-lime-700" : "bg-gray-100 text-gray-500"}`}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-black">{report.name}</p>
          <p className="mt-1 truncate text-xs font-medium text-gray-500">{report.path}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge value={report.kind} />
            <span className="text-xs font-medium text-gray-500">{formatBytes(report.size_bytes)}</span>
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
  onRetry,
}: {
  charts: ChartsResponse | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
}) {
  if (isLoading) return <LoadingBlock label="Đang tải chart index..." />;
  if (error) return <ErrorBlock error={error} onRetry={onRetry} />;
  if (!charts) return null;
  return (
    <section className="panel p-8">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Chart overview</h3>
          <p className="mt-1 text-sm font-medium text-gray-400">Nhóm biểu đồ do pipeline evaluation sinh ra.</p>
        </div>
        <BarChart3 className="h-5 w-5 text-gray-400" />
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {charts.groups.map((group) => (
          <div key={group.key} className="rounded-[24px] border border-gray-100 bg-gray-50 p-4">
            <p className="text-sm font-black text-gray-800">{group.title}</p>
            <p className="mt-2 text-3xl font-black text-gray-950">{group.charts.length}</p>
            <p className="text-xs font-medium text-gray-500">charts</p>
          </div>
        ))}
      </div>
      {charts.final_dashboard ? (
        <div className="mt-6">
          <p className="mb-3 text-xs font-black uppercase text-gray-400">Final quality dashboard</p>
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
  const content = useReportContent(report.path);
  if (content.isLoading) return <LoadingBlock label="Đang tải nội dung report..." />;
  if (content.error) return <ErrorBlock error={content.error} onRetry={() => content.refetch()} />;
  return (
    <section className="panel p-8">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-anton text-2xl font-black uppercase text-gray-900">{report.name}</h3>
          <p className="mt-1 text-xs font-medium text-gray-500">{report.path} · {formatDateTime(report.modified_at)}</p>
        </div>
        <StatusBadge value={report.kind} />
      </div>
      {report.kind === "markdown" ? (
        <article className="prose prose-slate max-w-none prose-headings:scroll-mt-20 prose-pre:rounded-2xl prose-pre:bg-gray-950 prose-pre:text-gray-100">
          <ReactMarkdown>{content.data || ""}</ReactMarkdown>
        </article>
      ) : (
        <pre className="max-h-[720px] overflow-auto rounded-[24px] bg-gray-950 p-4 text-xs leading-6 text-gray-100">
          {content.data}
        </pre>
      )}
    </section>
  );
}

function CsvReport({ path }: { path: string }) {
  const table = useReportTable(path, 200);
  if (table.isLoading) return <LoadingBlock label="Đang tải bảng CSV..." />;
  if (table.error) return <ErrorBlock error={table.error} onRetry={() => table.refetch()} />;
  const columns = (table.data?.columns || []).map((key) => ({ key, label: key }));
  return (
    <section className="panel p-8">
      <h3 className="mb-5 font-anton text-2xl font-black uppercase text-gray-900">{path}</h3>
      <DataTable rows={(table.data?.rows || []) as Record<string, unknown>[]} columns={columns} />
    </section>
  );
}

function JsonlReport({ path }: { path: string }) {
  const jsonl = useReportJsonl(path, 100);
  if (jsonl.isLoading) return <LoadingBlock label="Đang tải JSONL..." />;
  if (jsonl.error) return <ErrorBlock error={jsonl.error} onRetry={() => jsonl.refetch()} />;
  return (
    <section className="panel p-8">
      <h3 className="mb-5 font-anton text-2xl font-black uppercase text-gray-900">{path}</h3>
      <JsonPanel value={jsonl.data?.rows || []} />
    </section>
  );
}
