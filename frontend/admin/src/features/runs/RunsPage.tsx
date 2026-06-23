"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { adminApi } from "@/lib/admin-api";
import { formatDateTime } from "@/lib/format";
import type { WorkflowPreset } from "@/lib/types";
import { workflowPresets, workflowTitle } from "@/lib/workflows";

export function RunsPage() {
  const queryClient = useQueryClient();
  const [selectedPreset, setSelectedPreset] = useState<WorkflowPreset>(workflowPresets[0]);
  const [configText, setConfigText] = useState(() =>
    JSON.stringify(workflowPresets[0].defaultConfig, null, 2),
  );
  const [configError, setConfigError] = useState<string | null>(null);

  const runs = useQuery({
    queryKey: ["runs", "list"],
    queryFn: () => adminApi.listRuns({ limit: 50 }),
    refetchInterval: 10_000,
  });

  const createRun = useMutation({
    mutationFn: async () => {
      const config = parseConfig(configText);
      return adminApi.createRun(selectedPreset.id, config);
    },
    onSuccess: async () => {
      setConfigError(null);
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
    onError: (error) => {
      setConfigError(error instanceof Error ? error.message : String(error));
    },
  });

  const parsedPreview = useMemo(() => {
    try {
      return parseConfig(configText);
    } catch {
      return null;
    }
  }, [configText]);

  function selectPreset(preset: WorkflowPreset) {
    setSelectedPreset(preset);
    setConfigText(JSON.stringify(preset.defaultConfig, null, 2));
    setConfigError(null);
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-brand-700">Workflow runner</p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">Chạy và theo dõi milestone/workflow</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          UI tạo run qua FastAPI job runner. Mỗi run lưu metadata, step status, expected artifacts và log JSONL.
        </p>
      </div>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-3">
          {workflowPresets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => selectPreset(preset)}
              className={`focus-ring w-full rounded-lg border p-4 text-left transition ${
                selectedPreset.id === preset.id
                  ? "border-slate-950 bg-white shadow-panel"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-950">{preset.title}</h3>
                <StatusBadge value={preset.accent} />
              </div>
              <p className="mt-2 text-sm text-slate-500">{preset.description}</p>
            </button>
          ))}
        </div>

        <div className="panel p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">{selectedPreset.title}</h3>
              <p className="mt-1 text-sm text-slate-500">Có thể chỉnh config JSON trước khi chạy.</p>
            </div>
            <button
              type="button"
              disabled={createRun.isPending}
              onClick={() => createRun.mutate()}
              className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Play className="h-4 w-4" />
              {createRun.isPending ? "Đang tạo run..." : "Run"}
            </button>
          </div>
          <textarea
            value={configText}
            onChange={(event) => setConfigText(event.target.value)}
            spellCheck={false}
            className="focus-ring mt-4 min-h-[260px] w-full rounded-lg border border-slate-200 bg-slate-950 p-4 font-mono text-xs leading-6 text-slate-100"
          />
          {configError ? <p className="mt-3 text-sm text-red-600">{configError}</p> : null}
          {createRun.data ? (
            <Link
              className="mt-4 inline-flex rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700"
              href={`/admin/runs/${createRun.data.run.run_id}`}
            >
              Mở run vừa tạo: {createRun.data.run.run_id}
            </Link>
          ) : null}
          <div className="mt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Config preview</p>
            <JsonPanel value={parsedPreview || { error: "Invalid JSON" }} />
          </div>
        </div>
      </section>

      <section className="panel p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">Run history</h3>
            <p className="mt-1 text-sm text-slate-500">Tự refresh mỗi 10 giây khi đang mở trang.</p>
          </div>
          <button
            type="button"
            onClick={() => runs.refetch()}
            className="focus-ring inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
        {runs.isLoading ? <LoadingBlock /> : null}
        {runs.error ? <ErrorBlock error={runs.error} onRetry={() => runs.refetch()} /> : null}
        {runs.data ? (
          <DataTable
            rows={runs.data.items as unknown as Record<string, unknown>[]}
            columns={[
              {
                key: "run_id",
                label: "Run ID",
                render: (row) => (
                  <Link className="font-mono text-xs font-medium text-brand-700 hover:text-brand-800" href={`/admin/runs/${row.run_id}`}>
                    {String(row.run_id)}
                  </Link>
                ),
              },
              {
                key: "workflow_name",
                label: "Workflow",
                render: (row) => workflowTitle(String(row.workflow_name)),
              },
              { key: "status", label: "Status", render: (row) => <StatusBadge value={String(row.status)} /> },
              { key: "created_at", label: "Created", render: (row) => formatDateTime(String(row.created_at)) },
              {
                key: "steps",
                label: "Steps",
                render: (row) => (Array.isArray(row.steps) ? row.steps.length : 0),
              },
            ]}
          />
        ) : null}
      </section>
    </div>
  );
}

function parseConfig(value: string) {
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Config must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}
