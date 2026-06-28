"use client";

import { ReactFlow, ReactFlowProvider, Background, Controls, MarkerType, BackgroundVariant } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { getNodeStatus } from "../state";
import { WorkflowNode } from "./WorkflowNode";
import type { WorkflowNodeDefinition, WorkflowNodeId } from "../types";

type WorkflowGraphProps = {
  catalog: WorkflowNodeDefinition[];
  selectedNodeIds: WorkflowNodeId[];
  activeNodeId: WorkflowNodeId;
  onToggleNode: (nodeId: WorkflowNodeId) => void;
  onEditClick: (nodeId: WorkflowNodeId) => void;
  edgeLabels: Record<string, string>;
};

const nodePositions: Record<WorkflowNodeId, { x: number; y: number }> = {
  m00_runtime: { x: 50, y: 180 },
  m01_ingestion: { x: 330, y: 180 },
  m02_labeling: { x: 610, y: 30 },
  m03_rag: { x: 610, y: 330 },
  m04_retrieval: { x: 890, y: 30 },
  m06_extraction: { x: 1170, y: 180 },
  m07_verification: { x: 1450, y: 180 },
  m08_evaluation: { x: 1730, y: 30 },
};

const nodeTypes = {
  workflowNode: WorkflowNode,
};

function FlowCanvas({
  catalog,
  selectedNodeIds,
  activeNodeId,
  onToggleNode,
  onEditClick,
  edgeLabels,
}: WorkflowGraphProps) {
  const nodeById = Object.fromEntries(catalog.map((node) => [node.id, node])) as Record<
    WorkflowNodeId,
    WorkflowNodeDefinition
  >;

  // Map backend catalog specs to React Flow Nodes
  const nodes = catalog.map((node) => {
    const status = getNodeStatus(node.id, selectedNodeIds, nodeById);
    const isActive = activeNodeId === node.id;
    const dependsOnMilestones = node.dependsOn
      .map((depId) => nodeById[depId]?.milestone || "")
      .filter(Boolean);

    return {
      id: node.id,
      type: "workflowNode",
      position: nodePositions[node.id] || { x: 0, y: 0 },
      draggable: status !== "blocked",
      className: status === "blocked" ? "blocked-flow-node" : "",
      data: {
        node,
        status,
        isActive,
        onToggle: () => onToggleNode(node.id),
        onEditClick: () => onEditClick(node.id),
        dependsOnMilestones,
      },
    };
  });

  // Map backend catalog dependsOn links to React Flow Edges
  const edges = catalog.flatMap((node) => {
    return node.dependsOn.flatMap((depId) => {
      const isHighlighted = selectedNodeIds.includes(depId) && selectedNodeIds.includes(node.id);
      const edgeGroup = [];

      // Add a thicker, lighter green background line under the highlighted dashed line
      if (isHighlighted) {
        edgeGroup.push({
          id: `${depId}->${node.id}-bg`,
          source: depId,
          target: node.id,
          animated: false,
          style: {
            stroke: "rgba(120, 200, 65, 0.2)",
            strokeWidth: 12,
          },
        });
      }

      edgeGroup.push({
        id: `${depId}->${node.id}`,
        source: depId,
        target: node.id,
        animated: isHighlighted,
        label: edgeLabels[`${depId}->${node.id}`] || "",
        labelStyle: {
          fill: isHighlighted ? "#15803d" : "#64748B",
          fontWeight: 700,
          fontSize: 10,
          fontFamily: "Inter, sans-serif",
        },
        labelBgStyle: {
          fill: "#ffffff",
          fillOpacity: 0.1,
          rx: 6,
          ry: 6,
        },
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 6,
        style: isHighlighted
          ? { stroke: "#78C841", strokeWidth: 3 }
          : { stroke: "#CBD5E1", strokeWidth: 1.5, opacity: 0.6 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isHighlighted ? "#78C841" : "#CBD5E1",
          width: 16,
          height: 16,
        },
      });

      return edgeGroup;
    });
  });

  return (
    <div className="h-full w-full relative overflow-hidden bg-[#F8F9FA]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.02 }}
        zoomOnScroll={false}
        panOnScroll={false}
        preventScrolling={false}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.8} color="rgba(15, 23, 42, 0.20)" />
        <Controls className="!bg-white !border !border-slate-200 !shadow-sm !rounded-2xl" />
      </ReactFlow>
    </div>
  );
}

export function WorkflowGraph(props: WorkflowGraphProps) {
  return (
    <ReactFlowProvider>
      <FlowCanvas {...props} />
    </ReactFlowProvider>
  );
}
