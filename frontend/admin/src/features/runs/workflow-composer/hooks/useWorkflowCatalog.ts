import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/shared/utils/api";
import { workflowNodePresentation, workflowNodeOrder } from "../catalog";
import type { WorkflowNodeDefinition, WorkflowNodeId } from "../types";

export function useWorkflowCatalog() {
  return useQuery({
    queryKey: ["workflows", "catalog"],
    queryFn: async () => {
      const res = await adminApi.getWorkflowCatalog();
      const items = res.items || [];
      const edgeLabels = res.edge_labels || {};

      const catalog: WorkflowNodeDefinition[] = items.map((item: any) => {
        const id = item.id as WorkflowNodeId;
        const presentation = workflowNodePresentation[id] || {
          shortTitle: id,
          accent: "sky",
          icon: () => null,
        };

        return {
          id,
          milestone: item.milestone || "",
          title: item.title || "",
          description: item.description || "",
          dependsOn: (item.depends_on || []) as WorkflowNodeId[],
          defaultConfig: item.default_config || {},
          fields: (item.fields || []).map((f: any) => ({
            key: f.key,
            label: f.label,
            type: f.type,
            description: f.description,
            min: f.min,
            max: f.max,
            step: f.step,
            options: f.options,
            configurable: f.configurable ?? true,
          })),
          shortTitle: presentation.shortTitle,
          accent: presentation.accent,
          icon: presentation.icon,
        };
      });

      const sortedCatalog = catalog.sort((a, b) => {
        const idxA = workflowNodeOrder.indexOf(a.id);
        const idxB = workflowNodeOrder.indexOf(b.id);
        return idxA - idxB;
      });

      return {
        catalog: sortedCatalog,
        edgeLabels,
      };
    },
  });
}
