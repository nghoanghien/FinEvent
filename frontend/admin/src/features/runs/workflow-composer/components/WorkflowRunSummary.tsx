"use client";

import { AlertTriangle, CheckCircle2, Play, Route } from "lucide-react";
import type { WorkflowRunRequest, WorkflowNodeDefinition } from "../types";

type WorkflowRunSummaryProps = {
  request: WorkflowRunRequest;
  isPending: boolean;
  onRun: () => void;
  nodeById: Record<string, WorkflowNodeDefinition>;
};

export function WorkflowRunSummary({ request, isPending, onRun, nodeById }: WorkflowRunSummaryProps) {
  return (
    <div className="panel p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-black uppercase text-gray-400">Run control</p>
          <h3 className="mt-1 font-anton text-2xl font-black uppercase text-gray-900">
            Sẵn sàng chạy
          </h3>
        </div>
        <button
          type="button"
          disabled={!request.ok || isPending}
          onClick={onRun}
          className="finevent-primary-button disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Play className="h-4 w-4" />
          {isPending ? "Đang tạo run..." : "Run workflow"}
        </button>
      </div>

      <div className="mt-5 rounded-[24px] border border-gray-100 bg-gray-50 p-4">
        <div className="flex items-center gap-2 text-xs font-black uppercase text-gray-400">
          <Route className="h-4 w-4" />
          Execution path
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {request.selectedNodes.length > 0 ? (
            request.selectedNodes.map((nodeId) => {
              const node = nodeById[nodeId];
              return (
                <span
                  key={nodeId}
                  className="rounded-full bg-white px-3 py-1 text-xs font-black uppercase text-gray-700 shadow-sm border border-gray-100"
                >
                  {node ? `${node.milestone} ${node.shortTitle}` : nodeId}
                </span>
              );
            })
          ) : (
            <span className="text-sm font-semibold text-gray-400">Chưa có milestone nào được chọn.</span>
          )}
        </div>
      </div>

      {!request.ok ? (
        <div className="mt-4 flex items-start gap-3 rounded-[20px] border border-amber-100 bg-amber-50 p-4 text-amber-800">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <p className="text-sm font-bold">{request.message}</p>
        </div>
      ) : (
        <div className="mt-4 flex items-start gap-3 rounded-[20px] border border-lime-100 bg-lime-50 p-4 text-lime-800">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
          <p className="text-sm font-bold">Các dependency đã hợp lệ. Có thể tạo run.</p>
        </div>
      )}
    </div>
  );
}
