"use client";

import { useRouter } from "next/navigation";
import { Activity, BarChart3, Boxes, Database, FileText, RefreshCw, Server } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDateTime } from "@/shared/utils/format";
import type { AdminRun } from "@/shared/types";
import { workflowTitle } from "@/shared/constants/workflows";
import { useDashboard } from "./hooks/useDashboard";

export function DashboardPage() {
  const router = useRouter();
  const dashboard = useDashboard();
  const { health, runs, reports, charts, outputs } = dashboard;

  if (dashboard.isLoading) return <LoadingBlock />;
  if (dashboard.error && !health.data) return <ErrorBlock error={dashboard.error} onRetry={dashboard.refetch} />;

  const statusRows = statusChartData(runs.data?.items || []);
  const latestRun = runs.data?.items?.[0];

  return (
    <div className="eatzy-page space-y-8">
      <PageHeader
        eyebrow="Operational overview"
        title="FINEVENT CONTROL"
        icon={Activity}
        description="Theo dõi pipeline NLP/RAG thật: API, PostgreSQL/pgvector, workflow runs, reports, charts và structured outputs."
        actions={
          <>
            <button type="button" onClick={dashboard.refetch} className="eatzy-secondary-button">
              <RefreshCw className={`h-4 w-4 ${dashboard.isRefreshing ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <div onClick={() => router.push("/admin/runs")} className="eatzy-primary-button cursor-pointer">
              <Activity className="h-4 w-4" />
              Chạy workflow
            </div>
          </>
        }
      />

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="API" value={health.data?.api || "-"} description="FastAPI admin status" icon={Server} color="green" />
        <MetricCard
          title="PostgreSQL"
          value={health.data?.postgres || "-"}
          description={`pgvector: ${health.data?.pgvector || "-"}`}
          icon={Database}
          color="blue"
        />
        <MetricCard
          title="Reports"
          value={reports.data?.total ?? "-"}
          description="Markdown, CSV, JSONL, charts"
          icon={FileText}
          color="orange"
        />
        <MetricCard
          title="Outputs"
          value={outputs.data?.total ?? "-"}
          description="Structured extraction runs"
          icon={Boxes}
          color="purple"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="panel overflow-hidden">
          <div className="flex flex-col justify-between gap-4 bg-white p-8 pb-4 md:flex-row md:items-end">
            <div>
              <div className="mb-2 flex items-center gap-2">
                <div className="h-6 w-1.5 rounded-full bg-primary" />
                <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Run gần đây</h3>
              </div>
              <p className="pl-3.5 text-sm font-medium text-gray-400">Theo dõi nhanh các workflow vừa chạy.</p>
            </div>
            <div onClick={() => router.push("/admin/runs")} className="eatzy-secondary-button cursor-pointer">
              Xem tất cả
            </div>
          </div>
          <div className="p-5 pt-2">
            <DataTable
              rows={(runs.data?.items || []) as unknown as Record<string, unknown>[]}
              isLoading={runs.isLoading}
              columns={[
                {
                  key: "workflow_name",
                  label: "Workflow",
                  render: (row) => workflowTitle(String(row.workflow_name || "")),
                },
                {
                  key: "status",
                  label: "Status",
                  render: (row) => <StatusBadge value={String(row.status || "")} />,
                },
                {
                  key: "created_at",
                  label: "Created",
                  render: (row) => formatDateTime(String(row.created_at || "")),
                },
              ]}
              emptyText="Chưa có run nào. Hãy chạy workflow đầu tiên."
            />
          </div>
        </section>

        <section className="panel p-8">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Run status mix</h3>
              <p className="mt-1 text-sm font-medium text-gray-400">Tổng hợp 8 run mới nhất.</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-100 text-gray-500">
              <BarChart3 className="h-5 w-5" />
            </div>
          </div>
          <div className="mt-5 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusRows}>
                <XAxis dataKey="status" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#78C841" radius={[10, 10, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="panel p-8">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Health chi tiết</h3>
              <p className="mt-1 text-sm font-medium text-gray-400">Không hiển thị secret, chỉ hiển thị configured/unconfigured.</p>
            </div>
            <Server className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {[
              ["teacher_llm", health.data?.teacher_llm],
              ["student_llm", health.data?.student_llm],
              ["embedding", health.data?.embedding],
              ["data_dir", String(health.data?.artifacts.data_dir)],
              ["reports_dir", String(health.data?.artifacts.reports_dir)],
              ["runs_dir", String(health.data?.artifacts.runs_dir)],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-2xl border border-gray-100 bg-gray-50 p-3">
                <span className="text-sm font-medium text-gray-600">{label}</span>
                <StatusBadge value={value || "-"} />
              </div>
            ))}
          </div>
        </section>

        <section className="panel p-8">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Reports và charts</h3>
              <p className="mt-1 text-sm font-medium text-gray-400">Artifact mới nhất để mở nhanh khi demo.</p>
            </div>
            <BarChart3 className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-5 space-y-3">
            {charts.data?.final_dashboard ? (
              <div onClick={() => router.push("/admin/reports")} className="block rounded-2xl border border-primary/25 bg-lime-50 p-4 text-sm font-bold text-lime-800 cursor-pointer">
                Final quality dashboard đã sẵn sàng
              </div>
            ) : (
              <div className="rounded-2xl border border-warning/30 bg-orange-50 p-4 text-sm font-semibold text-orange-800">
                Chưa thấy final dashboard. Chạy workflow evaluation để sinh biểu đồ.
              </div>
            )}
            {(reports.data?.items || []).map((report) => (
              <div key={report.path} className="flex items-center justify-between gap-3 rounded-2xl border border-gray-100 p-3">
                <span className="truncate text-sm font-medium text-gray-700">{report.path}</span>
                <StatusBadge value={report.kind} />
              </div>
            ))}
          </div>
        </section>
      </div>

      {latestRun?.error_message ? <ErrorBlock title="Run mới nhất có lỗi" error={latestRun.error_message} /> : null}
    </div>
  );
}

function statusChartData(runs: AdminRun[]) {
  const counts = new Map<string, number>();
  for (const run of runs) counts.set(run.status, (counts.get(run.status) || 0) + 1);
  return ["success", "running", "queued", "failed", "canceled", "interrupted"].map((status) => ({
    status,
    count: counts.get(status) || 0,
  }));
}
