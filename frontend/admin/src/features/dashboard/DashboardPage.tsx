"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, BarChart3, Boxes, Database, FileText, Server } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { adminApi } from "@/lib/admin-api";
import { formatDateTime } from "@/lib/format";
import type { AdminRun } from "@/lib/types";
import { workflowTitle } from "@/lib/workflows";

export function DashboardPage() {
  const health = useQuery({ queryKey: ["admin-health"], queryFn: adminApi.health });
  const runs = useQuery({ queryKey: ["runs", "dashboard"], queryFn: () => adminApi.listRuns({ limit: 8 }) });
  const reports = useQuery({ queryKey: ["reports", "dashboard"], queryFn: () => adminApi.reports({ limit: 5 }) });
  const charts = useQuery({ queryKey: ["charts", "dashboard"], queryFn: adminApi.charts });
  const outputs = useQuery({ queryKey: ["outputs", "dashboard"], queryFn: () => adminApi.outputs({ limit: 5 }) });

  if (health.isLoading && runs.isLoading) return <LoadingBlock />;
  if (health.error) return <ErrorBlock error={health.error} onRetry={() => health.refetch()} />;

  const statusRows = statusChartData(runs.data?.items || []);
  const latestRun = runs.data?.items?.[0];

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-medium text-brand-700">Operational overview</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
            Theo dõi pipeline NLP/RAG từ dữ liệu đến báo cáo
          </h2>
          <p className="mt-2 max-w-3xl text-sm text-slate-500">
            Dashboard này tập trung vào workflow thật: trạng thái API, PostgreSQL/pgvector, run gần nhất,
            artifact reports, biểu đồ evaluation và output có cấu trúc.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="focus-ring rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white" href="/admin/runs">
            Chạy workflow
          </Link>
          <Link className="focus-ring rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-white" href="/admin/reports">
            Xem báo cáo
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="API" value={health.data?.api || "-"} description="FastAPI admin status" icon={Server} tone="emerald" />
        <MetricCard title="PostgreSQL" value={health.data?.postgres || "-"} description={`pgvector: ${health.data?.pgvector || "-"}`} icon={Database} tone="sky" />
        <MetricCard title="Reports" value={reports.data?.total ?? "-"} description="Markdown, CSV, JSONL, charts" icon={FileText} tone="amber" />
        <MetricCard title="Outputs" value={outputs.data?.total ?? "-"} description="Structured extraction runs" icon={Boxes} tone="slate" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="panel p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Run gần đây</h3>
              <p className="mt-1 text-sm text-slate-500">Theo dõi nhanh workflow vừa chạy.</p>
            </div>
            <Link href="/admin/runs" className="text-sm font-medium text-brand-700 hover:text-brand-800">
              Xem tất cả
            </Link>
          </div>
          <div className="mt-4">
            <DataTable
              rows={(runs.data?.items || []) as unknown as Record<string, unknown>[]}
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

        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Run status mix</h3>
              <p className="mt-1 text-sm text-slate-500">Tổng hợp 8 run mới nhất.</p>
            </div>
            <Activity className="h-5 w-5 text-slate-400" />
          </div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusRows}>
                <XAxis dataKey="status" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#16a34a" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Health chi tiết</h3>
              <p className="mt-1 text-sm text-slate-500">Không hiển thị secret, chỉ hiển thị configured/unconfigured.</p>
            </div>
            <Server className="h-5 w-5 text-slate-400" />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {[
              ["teacher_llm", health.data?.teacher_llm],
              ["student_llm", health.data?.student_llm],
              ["embedding", health.data?.embedding],
              ["data_dir", String(health.data?.artifacts.data_dir)],
              ["reports_dir", String(health.data?.artifacts.reports_dir)],
              ["runs_dir", String(health.data?.artifacts.runs_dir)],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                <span className="text-sm text-slate-600">{label}</span>
                <StatusBadge value={value || "-"} />
              </div>
            ))}
          </div>
        </section>

        <section className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Reports và charts</h3>
              <p className="mt-1 text-sm text-slate-500">Artifact mới nhất để mở nhanh khi demo.</p>
            </div>
            <BarChart3 className="h-5 w-5 text-slate-400" />
          </div>
          <div className="mt-4 space-y-3">
            {charts.data?.final_dashboard ? (
              <Link href="/admin/reports" className="block rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-medium text-emerald-800">
                Final quality dashboard đã sẵn sàng
              </Link>
            ) : (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                Chưa thấy final dashboard. Chạy workflow evaluation để sinh biểu đồ.
              </div>
            )}
            {(reports.data?.items || []).map((report) => (
              <div key={report.path} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3">
                <span className="truncate text-sm text-slate-700">{report.path}</span>
                <StatusBadge value={report.kind} />
              </div>
            ))}
          </div>
        </section>
      </div>

      {latestRun?.error_message ? (
        <ErrorBlock title="Run mới nhất có lỗi" error={latestRun.error_message} />
      ) : null}
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
