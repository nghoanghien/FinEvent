"use client";

import Link from "next/link";
import { Activity, Ban, ChevronLeft, ExternalLink, RefreshCw } from "lucide-react";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDateTime } from "@/lib/format";
import { workflowTitle } from "@/lib/workflows";
import { LiveLogViewer } from "./components/LiveLogViewer";
import { useCancelRun, useRunDetail } from "./hooks/useRuns";

export function RunDetailPage({ runId }: { runId: string }) {
  const run = useRunDetail(runId);
  const cancel = useCancelRun(runId);

  if (run.isLoading) return <LoadingBlock />;
  if (run.error) return <ErrorBlock error={run.error} onRetry={() => run.refetch()} />;
  if (!run.data) return null;

  const isCancelable = run.data.status === "queued" || run.data.status === "running";

  return (
    <div className="eatzy-page space-y-8">
      <PageHeader
        eyebrow="Run detail"
        title="WORKFLOW TRACE"
        icon={Activity}
        description={`${workflowTitle(run.data.workflow_name)} · ${run.data.run_id}`}
        actions={
          <>
            <Link href="/admin/runs" className="eatzy-secondary-button">
              <ChevronLeft className="h-4 w-4" />
              Quay lại
            </Link>
            <StatusBadge value={run.data.status} />
            <button type="button" onClick={() => run.refetch()} className="eatzy-secondary-button">
              <RefreshCw className={`h-4 w-4 ${run.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <button
              type="button"
              disabled={!isCancelable || cancel.isPending}
              onClick={() => cancel.mutate()}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-danger/20 bg-red-50 px-5 text-sm font-bold text-red-700 transition hover:-translate-y-0.5 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Ban className="h-4 w-4" />
              Cancel
            </button>
          </>
        }
      />

      <div className="grid gap-4 xl:grid-cols-4">
        <Info label="Created" value={formatDateTime(run.data.created_at)} />
        <Info label="Started" value={formatDateTime(run.data.started_at)} />
        <Info label="Finished" value={formatDateTime(run.data.finished_at)} />
        <Info label="Current step" value={run.data.current_step_id || "-"} />
      </div>

      {run.data.error_message ? <ErrorBlock title="Run error" error={run.data.error_message} /> : null}

      <section className="panel p-8">
        <div className="mb-5 flex items-center gap-2">
          <div className="h-6 w-1.5 rounded-full bg-primary" />
          <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Step timeline</h3>
        </div>
        <div className="grid gap-3">
          {run.data.steps.map((step, index) => (
            <div key={step.step_id} className="rounded-[24px] border border-gray-100 bg-white p-4 shadow-sm">
              <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-950 text-xs font-black text-white">
                      {index + 1}
                    </span>
                    <h4 className="text-sm font-black text-gray-950">{step.name}</h4>
                    <StatusBadge value={step.status} />
                  </div>
                  <p className="mt-2 truncate font-mono text-xs text-gray-500">{step.command?.join(" ")}</p>
                </div>
                <div className="text-xs font-medium text-gray-500 md:text-right">
                  <p>{step.milestone}</p>
                  <p>{formatDateTime(step.started_at)}</p>
                </div>
              </div>
              {step.expected_artifacts?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {step.expected_artifacts.map((artifact) => (
                    <span key={artifact} className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-1 font-mono text-xs font-medium text-gray-600">
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

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="panel p-8">
          <h3 className="mb-3 font-anton text-2xl font-black uppercase text-gray-900">Config</h3>
          <JsonPanel value={run.data.config} />
        </div>
        <div className="panel p-8">
          <h3 className="mb-3 font-anton text-2xl font-black uppercase text-gray-900">Summary</h3>
          <JsonPanel value={run.data.summary} />
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="panel p-5">
      <p className="text-xs font-black uppercase text-gray-400">{label}</p>
      <p className="mt-2 truncate text-sm font-bold text-gray-950">{value}</p>
    </div>
  );
}
