"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Activity, Play, RefreshCw } from "lucide-react";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorBlock } from "@/components/ui/StateBlock";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableToolbar } from "@/components/ui/TableToolbar";
import { formatDateTime } from "@/shared/utils/format";
import type { WorkflowPreset } from "@/shared/types";
import { workflowPresets, workflowTitle } from "@/shared/constants/workflows";
import { useCreateRun, useRunsList } from "./hooks/useRuns";

export function RunsPage() {
  const router = useRouter();
  const [selectedPreset, setSelectedPreset] = useState<WorkflowPreset>(workflowPresets[0]);
  const [configText, setConfigText] = useState(() => JSON.stringify(workflowPresets[0].defaultConfig, null, 2));
  const [configError, setConfigError] = useState<string | null>(null);

  const runs = useRunsList(50);
  const createRun = useCreateRun();

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

  function handleRun() {
    let config: Record<string, unknown>;
    try {
      config = parseConfig(configText);
      setConfigError(null);
    } catch (error) {
      setConfigError(error instanceof Error ? error.message : String(error));
      return;
    }
    createRun.mutate(
      { workflowName: selectedPreset.id, config },
      {
        onError: (error) => setConfigError(error instanceof Error ? error.message : String(error)),
      },
    );
  }

  return (
    <div className="eatzy-page space-y-8">
      <PageHeader
        eyebrow="Workflow runner"
        title="PIPELINE RUNNER"
        icon={Activity}
        description="Tạo run qua FastAPI job runner. Mỗi run lưu metadata, step status, expected artifacts và log JSONL để UI theo dõi trực tiếp."
        actions={
          <button type="button" onClick={() => runs.refetch()} className="eatzy-secondary-button">
            <RefreshCw className={`h-4 w-4 ${runs.isFetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-3">
          {workflowPresets.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => selectPreset(preset)}
              className={`focus-ring w-full rounded-[28px] border p-5 text-left transition-all duration-300 ${
                selectedPreset.id === preset.id
                  ? "border-primary/40 bg-white shadow-[inset_0_0_24px_16px_rgba(255,255,255,0.9),0_12px_35px_rgba(120,200,65,0.12)]"
                  : "border-gray-100 bg-white hover:-translate-y-0.5 hover:shadow-eatzy-hover"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-anton text-xl font-black uppercase text-gray-900">{preset.title}</h3>
                <StatusBadge value={preset.accent} />
              </div>
              <p className="mt-2 text-sm font-medium text-gray-500">{preset.description}</p>
            </button>
          ))}
        </div>

        <div className="panel p-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-anton text-2xl font-black uppercase text-gray-900">{selectedPreset.title}</h3>
              <p className="mt-1 text-sm font-medium text-gray-400">Có thể chỉnh config JSON trước khi chạy.</p>
            </div>
            <button type="button" disabled={createRun.isPending} onClick={handleRun} className="eatzy-primary-button disabled:cursor-not-allowed disabled:opacity-60">
              <Play className="h-4 w-4" />
              {createRun.isPending ? "Đang tạo run..." : "Run"}
            </button>
          </div>
          <textarea
            value={configText}
            onChange={(event) => setConfigText(event.target.value)}
            spellCheck={false}
            className="focus-ring mt-5 min-h-[260px] w-full rounded-[24px] border border-gray-900 bg-gray-950 p-4 font-mono text-xs leading-6 text-gray-100"
          />
          {configError ? <p className="mt-3 text-sm font-semibold text-danger">{configError}</p> : null}
          {createRun.data ? (
            <div onClick={() => router.push(`/admin/runs/${createRun.data.run.run_id}`)} className="mt-4 inline-flex cursor-pointer rounded-full border border-primary/30 bg-lime-50 px-4 py-2 text-sm font-bold text-lime-700">
              Mở run vừa tạo: {createRun.data.run.run_id}
            </div>
          ) : null}
          <div className="mt-5">
            <p className="mb-2 text-xs font-black uppercase text-gray-400">Config preview</p>
            <JsonPanel value={parsedPreview || { error: "Invalid JSON" }} />
          </div>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <TableToolbar
          title="Run history"
          description="Tự refresh mỗi 10 giây khi đang mở trang."
          onRefresh={() => runs.refetch()}
          isRefreshing={runs.isFetching}
        />
        <div className="p-5 pt-2">
          {runs.error ? <ErrorBlock error={runs.error} onRetry={() => runs.refetch()} /> : null}
          <DataTable
            rows={(runs.data?.items || []) as unknown as Record<string, unknown>[]}
            isLoading={runs.isLoading}
            columns={[
              {
                key: "run_id",
                label: "Run ID",
                render: (row) => (
                  <div onClick={() => router.push(`/admin/runs/${row.run_id}`)} className="font-mono text-xs font-bold text-lime-700 hover:text-lime-800 cursor-pointer">
                    {String(row.run_id)}
                  </div>
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
        </div>
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
