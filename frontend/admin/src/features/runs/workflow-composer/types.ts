import type { LucideIcon } from "lucide-react";

export type WorkflowNodeId =
  | "m00_runtime"
  | "m01_ingestion"
  | "m02_labeling"
  | "m03_rag"
  | "m04_retrieval"
  | "m06_extraction"
  | "m07_verification"
  | "m08_evaluation";

export type WorkflowFieldType = "text" | "number" | "select" | "checkbox" | "multi-select";

export type WorkflowFieldOption = {
  value: string;
  label: string;
};

export type WorkflowFieldDefinition = {
  key: string;
  label: string;
  type: WorkflowFieldType;
  description?: string;
  min?: number;
  max?: number;
  step?: number;
  options?: WorkflowFieldOption[];
  configurable?: boolean;
};

export function isConfigurableField(field: WorkflowFieldDefinition) {
  return field.configurable !== false;
}

export function isNodeConfigurable(node: WorkflowNodeDefinition) {
  if (!node.fields || node.fields.length === 0) return false;
  return node.fields.some(isConfigurableField);
}

export type WorkflowNodeDefinition = {
  id: WorkflowNodeId;
  milestone: string;
  title: string;
  shortTitle: string;
  description: string;
  accent: "sky" | "emerald" | "amber";
  icon: LucideIcon;
  dependsOn: WorkflowNodeId[];
  defaultConfig: Record<string, unknown>;
  fields: WorkflowFieldDefinition[];
};

export type WorkflowNodeStatus = "selected" | "available" | "blocked";

export type WorkflowComposerState = {
  selectedNodeIds: WorkflowNodeId[];
  activeNodeId: WorkflowNodeId;
  configs: Record<WorkflowNodeId, Record<string, unknown>>;
  editingNodeId?: WorkflowNodeId | null;
};

export type WorkflowRunRequest =
  | {
    ok: true;
    workflowName: "milestone_graph";
    config: Record<string, unknown>;
    selectedNodes: WorkflowNodeId[];
  }
  | {
    ok: false;
    message: string;
    selectedNodes: WorkflowNodeId[];
    config: Record<string, unknown>;
  };
