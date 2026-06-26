import type {
  WorkflowComposerState,
  WorkflowNodeDefinition,
  WorkflowNodeId,
  WorkflowNodeStatus,
  WorkflowRunRequest,
} from "./types";

export function createInitialWorkflowComposerState(
  catalog: WorkflowNodeDefinition[],
): WorkflowComposerState {
  return {
    selectedNodeIds: [],
    activeNodeId: "m00_runtime",
    configs: Object.fromEntries(
      catalog.map((node) => [node.id, { ...node.defaultConfig }]),
    ) as Record<WorkflowNodeId, Record<string, unknown>>,
    editingNodeId: null,
  };
}

export function getNodeStatus(
  nodeId: WorkflowNodeId,
  selectedNodeIds: WorkflowNodeId[],
  nodeById: Record<WorkflowNodeId, WorkflowNodeDefinition>,
): WorkflowNodeStatus {
  if (selectedNodeIds.includes(nodeId)) return "selected";
  const node = nodeById[nodeId];
  if (!node) return "blocked";
  return node.dependsOn.every((dependency) => selectedNodeIds.includes(dependency))
    ? "available"
    : "blocked";
}

export function toggleWorkflowNode(
  state: WorkflowComposerState,
  nodeId: WorkflowNodeId,
  nodeById: Record<WorkflowNodeId, WorkflowNodeDefinition>,
  nodeOrder: WorkflowNodeId[],
): WorkflowComposerState {
  const status = getNodeStatus(nodeId, state.selectedNodeIds, nodeById);
  if (status === "blocked") return state;

  if (status === "selected") {
    const selectedNodeIds = state.selectedNodeIds.filter(
      (selectedId) => selectedId !== nodeId && !dependsOnNode(selectedId, nodeId, nodeById),
    );
    return {
      ...state,
      selectedNodeIds,
      activeNodeId: selectedNodeIds[selectedNodeIds.length - 1] || "m00_runtime",
      editingNodeId: state.editingNodeId === nodeId ? null : state.editingNodeId,
    };
  }

  const selectedNodeIds = sortWorkflowNodes([...state.selectedNodeIds, nodeId], nodeOrder);
  return {
    ...state,
    selectedNodeIds,
    activeNodeId: nodeId,
  };
}

export function updateNodeConfig(
  state: WorkflowComposerState,
  nodeId: WorkflowNodeId,
  key: string,
  value: unknown,
): WorkflowComposerState {
  return {
    ...state,
    activeNodeId: nodeId,
    configs: {
      ...state.configs,
      [nodeId]: {
        ...state.configs[nodeId],
        [key]: value,
      },
    },
  };
}

export function setActiveNode(
  state: WorkflowComposerState,
  nodeId: WorkflowNodeId,
): WorkflowComposerState {
  return { ...state, activeNodeId: nodeId };
}

export function buildWorkflowRunRequest(
  state: WorkflowComposerState,
  nodeById: Record<WorkflowNodeId, WorkflowNodeDefinition>,
  nodeOrder: WorkflowNodeId[],
): WorkflowRunRequest {
  const selectedNodes = sortWorkflowNodes(state.selectedNodeIds, nodeOrder);
  const config = {
    ...selectedNodes.reduce<Record<string, unknown>>(
      (merged, nodeId) => ({ ...merged, ...normalizeNodeConfig(state.configs[nodeId]) }),
      {},
    ),
    selected_nodes: selectedNodes,
    node_configs: Object.fromEntries(
      selectedNodes.map((nodeId) => [nodeId, normalizeNodeConfig(state.configs[nodeId])]),
    ),
  };

  if (selectedNodes.length === 0) {
    return {
      ok: false,
      message: "Chọn ít nhất một milestone trước khi chạy workflow.",
      selectedNodes,
      config,
    };
  }

  const dependencyMessage = validateDependencies(selectedNodes, nodeById);
  if (dependencyMessage) {
    return { ok: false, message: dependencyMessage, selectedNodes, config };
  }

  const configMessage = validateSelectedConfigs(selectedNodes, state.configs);
  if (configMessage) {
    return { ok: false, message: configMessage, selectedNodes, config };
  }

  return {
    ok: true,
    workflowName: "milestone_graph",
    selectedNodes,
    config,
  };
}

function validateDependencies(
  selectedNodeIds: WorkflowNodeId[],
  nodeById: Record<WorkflowNodeId, WorkflowNodeDefinition>,
) {
  const selected = new Set(selectedNodeIds);
  for (const nodeId of selectedNodeIds) {
    const node = nodeById[nodeId];
    if (!node) continue;
    const missing = node.dependsOn.filter((dependency) => !selected.has(dependency));
    if (missing.length > 0) {
      return `${node.milestone} cần chạy sau ${missing.map((id) => nodeById[id]?.milestone || id).join(", ")}.`;
    }
  }
  return null;
}

function validateSelectedConfigs(
  selectedNodeIds: WorkflowNodeId[],
  configs: WorkflowComposerState["configs"],
) {
  if (selectedNodeIds.includes("m01_ingestion")) {
    const config = configs.m01_ingestion;
    if (config) {
      const maxArticles = Number(config.max_articles);
      if (!Number.isInteger(maxArticles) || maxArticles < 1) {
        return "M01: số bài tải/xử lý phải là số nguyên từ 1 trở lên.";
      }
    }
  }
  if (selectedNodeIds.includes("m06_extraction")) {
    const config = configs.m06_extraction;
    if (config) {
      const limit = Number(config.limit);
      const offset = Number(config.offset);
      if (!Number.isInteger(limit) || limit < 1) return "M06: số bài chạy phải là số nguyên từ 1 trở lên.";
      if (!Number.isInteger(offset) || offset < 0) return "M06: offset phải là số nguyên không âm.";
      if (!String(config.output_path || "").trim()) return "M06: predictions output không được để trống.";
    }
  }
  return null;
}

function dependsOnNode(
  nodeId: WorkflowNodeId,
  dependencyId: WorkflowNodeId,
  nodeById: Record<WorkflowNodeId, WorkflowNodeDefinition>,
): boolean {
  const node = nodeById[nodeId];
  if (!node) return false;
  return node.dependsOn.some(
    (candidate) => candidate === dependencyId || dependsOnNode(candidate, dependencyId, nodeById),
  );
}

function sortWorkflowNodes(nodeIds: WorkflowNodeId[], nodeOrder: WorkflowNodeId[]): WorkflowNodeId[] {
  const unique = Array.from(new Set(nodeIds));
  return nodeOrder.filter((nodeId) => unique.includes(nodeId));
}

function normalizeNodeConfig(config: Record<string, unknown>) {
  if (!config) return {};
  return Object.fromEntries(
    Object.entries(config).map(([key, value]) => {
      if (typeof value === "string") return [key, value.trim()];
      if (Array.isArray(value)) {
        return [
          key,
          value.filter((item): item is string => typeof item === "string" && Boolean(item.trim())),
        ];
      }
      return [key, value];
    }),
  );
}
