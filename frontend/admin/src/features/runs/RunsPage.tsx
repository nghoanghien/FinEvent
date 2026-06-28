"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Activity, Play, Settings } from "lucide-react";
import { ErrorBlock } from "@/components/ui/StateBlock";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useCreateRun } from "./hooks/useRuns";
import { useSidebar } from "@/components/layout/SidebarContext";
import {
  useWorkflowComposer,
  WorkflowGraph,
  NodeConfigDrawer,
  ConfigModal,
  RunConfirmModal,
} from "./workflow-composer";

export function RunsPage() {
  const router = useRouter();
  const composer = useWorkflowComposer();
  const {
    catalog,
    nodeById,
    isLoading: isCatalogLoading,
    composerState,
    runRequest,
    handleToggleNode,
    handleUpdateConfig,
    handleSetActiveNode,
    handleSetEditingNode,
    edgeLabels,
  } = composer;

  const [configError, setConfigError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  const { isExpanded } = useSidebar();
  const createRun = useCreateRun();

  function handleRunClick() {
    if (!runRequest.ok) {
      setConfigError(runRequest.message);
      return;
    }
    setConfigError(null);
    setIsConfirmOpen(true);
  }

  function handleConfirmRun() {
    setIsConfirmOpen(false);
    if (!runRequest.ok) return;
    createRun.mutate(
      { workflowName: runRequest.workflowName, config: runRequest.config },
      {
        onError: (error) => setConfigError(error instanceof Error ? error.message : String(error)),
      },
    );
  }

  return (
    <div className="relative overflow-hidden -mx-4 md:-mx-8 -mt-4 -mb-10 h-screen flex flex-col justify-stretch bg-[#F8F9FA]">
      {/* Individual Fixed PageHeader (No frame wrapper/borders/backgrounds) */}
      <div
        className={`fixed top-4 z-30 transition-all duration-500 ease-out left-4 ${isExpanded ? "md:left-[320px]" : "md:left-[112px]"
          }`}
      >
        <PageHeader
          eyebrow="Workflow runner"
          title="PIPELINE RUNNER"
          icon={Activity}
          minimal={true}
        />
      </div>

      {/* Individual Fixed Warning Message (Top Center, No frame wrapper) */}
      {!runRequest.ok && runRequest.message ? (
        <div className="fixed top-6 left-1/2 z-50 -translate-x-1/2 pointer-events-none">
          <span className="inline-block whitespace-nowrap rounded-full bg-rose-50 border border-rose-100 px-3.5 py-1.5 text-xs font-bold text-rose-600 shadow-sm animate-[fadeInDown_0.2s_ease-out]">
            {runRequest.message}
          </span>
        </div>
      ) : null}

      {/* Individual Fixed Run & Settings controls (No frame wrapper/borders/backgrounds) */}
      <div className="fixed top-6 right-4 md:right-8 z-30 flex items-center gap-3">
        <button
          type="button"
          onClick={() => setIsDrawerOpen(!isDrawerOpen)}
          className={`focus-ring flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-200 ${isDrawerOpen
            ? "border-slate-800 bg-slate-800 text-white shadow-[inset_0_2px_8px_rgba(0,0,0,0.3)] scale-95"
            : "border-slate-300 bg-slate-100 text-slate-700 shadow-[0_4px_12px_rgba(15,23,42,0.1)] hover:bg-slate-200 hover:border-slate-400 hover:text-slate-900 hover:shadow-[0_6px_16px_rgba(15,23,42,0.15)]"
            }`}
          title="Cấu hình Node"
        >
          <Settings className={`h-5 w-5 transition-transform duration-300 ${isDrawerOpen ? "rotate-90" : "rotate-0"}`} />
        </button>

        <button
          type="button"
          disabled={!runRequest.ok || createRun.isPending}
          onClick={handleRunClick}
          className="finevent-primary-button disabled:cursor-not-allowed disabled:opacity-50 shrink-0"
        >
          <Play className="h-4 w-4" />
          {createRun.isPending ? "Đang chạy..." : "Run workflow"}
        </button>
      </div>

      {isCatalogLoading ? (
        <div className="flex-1 flex flex-col gap-4 items-center justify-center bg-[#F8F9FA]">
          <LoadingSpinner />
          <p className="text-sm font-bold text-gray-400 uppercase tracking-widest">
            Đang tải dữ liệu Graph...
          </p>
        </div>
      ) : (
        <>
          <div className="flex-1 h-full min-h-0 relative z-0">
            <WorkflowGraph
              catalog={catalog}
              selectedNodeIds={composerState.selectedNodeIds}
              activeNodeId={composerState.activeNodeId}
              onToggleNode={handleToggleNode}
              onEditClick={handleSetEditingNode}
              edgeLabels={edgeLabels}
            />
          </div>

          {/* Configuration Drawer */}
          <NodeConfigDrawer
            isOpen={isDrawerOpen}
            onClose={() => setIsDrawerOpen(false)}
            runRequest={runRequest}
            composerState={composerState}
            nodeById={nodeById}
            onChange={handleUpdateConfig}
            onSetActiveNode={handleSetActiveNode}
          />

          {/* Node Settings Modal */}
          <ConfigModal
            isOpen={composerState.editingNodeId !== null && composerState.editingNodeId !== undefined}
            node={composerState.editingNodeId ? nodeById[composerState.editingNodeId] : null}
            configs={composerState.editingNodeId ? composerState.configs[composerState.editingNodeId] : undefined}
            onChange={(key, val) => {
              if (composerState.editingNodeId) {
                handleUpdateConfig(composerState.editingNodeId, key, val);
              }
            }}
            onClose={() => handleSetEditingNode(null)}
          />

          {/* Run Confirmation Modal */}
          {runRequest.ok && (
            <RunConfirmModal
              isOpen={isConfirmOpen}
              workflowName={runRequest.workflowName}
              selectedNodeIds={composerState.selectedNodeIds}
              nodeById={nodeById}
              isPending={createRun.isPending}
              onConfirm={handleConfirmRun}
              onClose={() => setIsConfirmOpen(false)}
            />
          )}
        </>
      )}

      {/* Floating feedback / success notifications */}
      <div className="fixed bottom-6 left-6 z-30 flex flex-col gap-3 max-w-md pointer-events-auto">
        {configError ? <ErrorBlock title="Không tạo được run" error={configError} /> : null}
        {createRun.data ? (
          <button
            type="button"
            onClick={() => router.push(`/admin/runs/${createRun.data.run.run_id}`)}
            className="finevent-secondary-button border-primary/30 bg-lime-50 text-lime-800 animate-[fadeInUp_0.3s_ease-out] shadow-lg"
          >
            <Play className="h-4 w-4" />
            Mở run vừa tạo: {createRun.data.run.run_id}
          </button>
        ) : null}
      </div>
    </div>
  );
}
