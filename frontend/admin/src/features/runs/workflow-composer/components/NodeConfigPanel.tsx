"use client";

import { useMemo } from "react";
import { Settings2 } from "lucide-react";
import { ConfigField } from "./ConfigField";
import {
  isConfigurableField,
  isNodeConfigurable,
  type WorkflowComposerState,
  type WorkflowNodeDefinition,
  type WorkflowNodeId,
} from "../types";

type NodeConfigPanelProps = {
  state: WorkflowComposerState;
  nodeById: Record<string, WorkflowNodeDefinition>;
  onChange: (nodeId: WorkflowNodeId, key: string, value: any) => void;
  onSetActiveNode: (nodeId: WorkflowNodeId) => void;
  flat?: boolean;
};

export function NodeConfigPanel({ state, nodeById, onChange, onSetActiveNode, flat = false }: NodeConfigPanelProps) {
  const selectedNodeIds = state.selectedNodeIds;

  const configurableSelectedNodeIds = useMemo(() => {
    return selectedNodeIds.filter((nodeId) => {
      const node = nodeById[nodeId];
      return node && isNodeConfigurable(node);
    });
  }, [selectedNodeIds, nodeById]);

  const activeNodeId = configurableSelectedNodeIds.includes(state.activeNodeId)
    ? state.activeNodeId
    : configurableSelectedNodeIds[0];

  return (
    <div className={flat ? "" : "panel p-6"}>
      {!flat && (
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase text-gray-400">Node config</p>
            <h3 className="mt-1 font-anton text-2xl font-black uppercase text-gray-900">Cấu hình node chạy</h3>
          </div>
          <Settings2 className="h-5 w-5 text-gray-400" />
        </div>
      )}

      {configurableSelectedNodeIds.length === 0 ? (
        <div className="mt-6 rounded-[24px] border border-dashed border-gray-200 bg-gray-50 p-6">
          <p className="text-sm font-semibold text-gray-500">Chọn milestone để bắt đầu cấu hình workflow.</p>
        </div>
      ) : (
        <>
          <div className="mt-0 flex flex-wrap gap-2">
            {configurableSelectedNodeIds.map((nodeId) => {
              const node = nodeById[nodeId];
              if (!node) return null;
              const isActive = nodeId === activeNodeId;
              return (
                <button
                  key={nodeId}
                  type="button"
                  onClick={() => onSetActiveNode(nodeId)}
                  className={[
                    "focus-ring inline-flex h-10 items-center gap-2 rounded-full border px-4 text-sm font-bold transition",
                    isActive
                      ? "border-primary bg-lime-50 text-gray-950 shadow-sm"
                      : "border-gray-100 bg-white text-gray-500 hover:text-gray-900 hover:border-gray-200",
                  ].join(" ")}
                >
                  <span className="text-xs font-black uppercase text-gray-400">{node.milestone}</span>
                  {node.shortTitle}
                </button>
              );
            })}
          </div>

          {activeNodeId && nodeById[activeNodeId] ? (
            <div className="mt-6 space-y-4">
              {(() => {
                const configurableFields = nodeById[activeNodeId].fields.filter(isConfigurableField);
                if (configurableFields.length > 0) {
                  return configurableFields.map((field) => (
                    <ConfigField
                      key={field.key}
                      field={field}
                      value={state.configs[activeNodeId]?.[field.key]}
                      onChange={(value) => onChange(activeNodeId, field.key, value)}
                    />
                  ));
                }
                return (
                  <div className="rounded-[24px] border border-dashed border-gray-200 bg-gray-50 p-6">
                    <p className="text-sm font-semibold text-gray-500">
                      Node này không cần cấu hình thủ công.
                    </p>
                  </div>
                );
              })()}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
