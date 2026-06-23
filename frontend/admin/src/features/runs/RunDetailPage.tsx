"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, ExternalLink, RefreshCw } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { adminApi } from "@/lib/admin-api";
import { formatDateTime } from "@/lib/format";
import { workflowTitle } from "@/lib/workflows";
import { LiveLogViewer } from "./components/LiveLogViewer";

export function RunDetailPage({ runId }: { runId: string }) {
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: ["runs", runId],
    queryFn: () => adminApi.getRun(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "queued" ? 5_000 : false;
    },
  });

  const cancel = useMutation({
    mutationFn: () => adminApi.cancelRun(runId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
  });

  if (run.isLoading) return <LoadingBlock />;
  if (run.error) return <ErrorBlock error={run.error} onRetry={() => run.refetch()} />;
  if (!run.data) return null;

  const isCancelable = run.data.status === "queued" || run.data.status === "running";

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div className="min-w-0">
          <Link href="/admin/runs" className="text-sm font-medium text-brand-700 hover:text-brand-800">
            ← Quay lại workflow
          </Link>
          <h2 className="mt-2 break-all text-2xl font-semibold text-slate-950">{run.data.run_id}</h2>
          <p className="mt-1 text-sm text-slate-500">{workflowTitle(run.data.workflow_name)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge value={run.data.status} />
          <button
            type="button"
            onClick={() => run.refetch()}
            className="focus-ring inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            type="button"
            disabled={!isCancelable || cancel.isPending}
            onClick={() => cancel.mutate()}
            className="focus-ring inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Ban className="h-4 w-4" />
            Cancel
          </button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-4">
        <Info label="Created" value={formatDateTime(run.data.created_at)} />
        <Info label="Started" value={formatDateTime(run.data.started_at)} />
        <Info label="Finished" value={formatDateTime(run.data.finished_at)} />
        <Info label="Current step" value={run.data.current_step_id || "-"} />
      </div>

      {run.data.error_message ? <ErrorBlock title="Run error" error={run.data.error_message} /> : null}

      <section className="panel p-5">
        <h3 className="text-sm font-semibold text-slate-950">Step timeline</h3>
        <div className="mt-4 grid gap-3">
          {run.data.steps.map((step, index) => (
            <div key={step.step_id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-950 text-xs font-semibold text-white">
                      {index + 1}
                    </span>
                    <h4 className="text-sm font-semibold text-slate-950">{step.name}</h4>
                    <StatusBadge value={step.status} />
                  </div>
                  <p className="mt-2 font-mono text-xs text-slate-500">{step.command?.join(" ")}</p>
                </div>
                <div className="text-xs text-slate-500">
                  <p>{step.milestone}</p>
                  <p>{formatDateTime(step.started_at)}</p>
                </div>
              </div>
              {step.expected_artifacts?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {step.expected_artifacts.map((artifact) => (
                    <span key={artifact} className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 font-mono text-xs text-slate-600">
                      <ExternalLink className="h-3 w-3" />
                      {artifact}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      <LiveLogViewer runId={runId} enabled={run.data.status === "running" || run.data.status === "queued"} />

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="panel p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-950">Config</h3>
          <JsonPanel value={run.data.config} />
        </div>
        <div className="panel p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-950">Summary</h3>
          <JsonPanel value={run.data.summary} />
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 truncate text-sm font-semibold text-slate-950">{value}</p>
    </div>
  );
}
