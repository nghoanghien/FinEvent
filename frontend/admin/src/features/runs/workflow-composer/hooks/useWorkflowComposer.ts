import { useEffect, useMemo, useState } from "react";
import { useWorkflowCatalog } from "./useWorkflowCatalog";
import {
  buildWorkflowRunRequest,
  createInitialWorkflowComposerState,
  setActiveNode,
  toggleWorkflowNode,
  updateNodeConfig,
} from "../state";
import { workflowNodeOrder } from "../catalog";
import type { WorkflowComposerState, WorkflowNodeDefinition, WorkflowNodeId, WorkflowRunRequest } from "../types";

export function useWorkflowComposer() {
  const { data, isLoading } = useWorkflowCatalog();
  const catalog = useMemo(() => data?.catalog || [], [data?.catalog]);
  const edgeLabels = useMemo(() => data?.edgeLabels || {}, [data?.edgeLabels]);

  const [composerState, setComposerState] = useState<WorkflowComposerState>({
    selectedNodeIds: [],
    activeNodeId: "m00_runtime",
    configs: {} as Record<WorkflowNodeId, Record<string, unknown>>,
    editingNodeId: null,
  });

  useEffect(() => {
    if (catalog.length > 0 && Object.keys(composerState.configs).length === 0) {
      setComposerState(createInitialWorkflowComposerState(catalog));
    }
  }, [catalog, composerState.configs]);

  const nodeById = useMemo(() => {
    return Object.fromEntries(catalog.map((node) => [node.id, node])) as Record<
      WorkflowNodeId,
      WorkflowNodeDefinition
    >;
  }, [catalog]);

  const runRequest = useMemo<WorkflowRunRequest>(() => {
    if (catalog.length === 0) {
      return {
        ok: false,
        message: "Đang tải catalog...",
        selectedNodes: [] as WorkflowNodeId[],
        config: {} as Record<string, unknown>,
      };
    }
    return buildWorkflowRunRequest(composerState, nodeById, workflowNodeOrder);
  }, [composerState, catalog, nodeById]);

  function handleToggleNode(nodeId: WorkflowNodeId) {
    setComposerState((current) => toggleWorkflowNode(current, nodeId, nodeById, workflowNodeOrder));
  }

  function handleUpdateConfig(nodeId: WorkflowNodeId, key: string, value: unknown) {
    setComposerState((current) => updateNodeConfig(current, nodeId, key, value));
  }

  function handleSetActiveNode(nodeId: WorkflowNodeId) {
    setComposerState((current) => setActiveNode(current, nodeId));
  }

  function handleSetEditingNode(nodeId: WorkflowNodeId | null) {
    setComposerState((current) => ({
      ...current,
      editingNodeId: nodeId,
    }));
  }

  function resetComposer() {
    if (catalog.length > 0) {
      setComposerState(createInitialWorkflowComposerState(catalog));
    }
  }

  return {
    catalog,
    nodeById,
    isLoading,
    composerState,
    runRequest,
    handleToggleNode,
    handleUpdateConfig,
    handleSetActiveNode,
    handleSetEditingNode,
    resetComposer,
    edgeLabels,
  };
}
