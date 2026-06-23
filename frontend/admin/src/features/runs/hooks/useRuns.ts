import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/shared/utils/api";

export function useRunsList(limit = 50) {
  return useQuery({
    queryKey: ["runs", "list", limit],
    queryFn: () => adminApi.listRuns({ limit }),
    refetchInterval: 10_000,
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ workflowName, config }: { workflowName: string; config: Record<string, unknown> }) =>
      adminApi.createRun(workflowName, config),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-health"] });
    },
  });
}

export function useRunDetail(runId: string) {
  return useQuery({
    queryKey: ["runs", runId],
    queryFn: () => adminApi.getRun(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "queued" ? 5_000 : false;
    },
  });
}

export function useCancelRun(runId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => adminApi.cancelRun(runId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      await queryClient.invalidateQueries({ queryKey: ["run-logs", runId] });
    },
  });
}
