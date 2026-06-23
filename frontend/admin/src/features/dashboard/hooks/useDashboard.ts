import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";

export function useDashboard() {
  const health = useQuery({ queryKey: ["admin-health", "dashboard"], queryFn: adminApi.health });
  const runs = useQuery({ queryKey: ["runs", "dashboard"], queryFn: () => adminApi.listRuns({ limit: 8 }) });
  const reports = useQuery({ queryKey: ["reports", "dashboard"], queryFn: () => adminApi.reports({ limit: 5 }) });
  const charts = useQuery({ queryKey: ["charts", "dashboard"], queryFn: adminApi.charts });
  const outputs = useQuery({ queryKey: ["outputs", "dashboard"], queryFn: () => adminApi.outputs({ limit: 5 }) });

  const refetch = async () => {
    await Promise.all([health.refetch(), runs.refetch(), reports.refetch(), charts.refetch(), outputs.refetch()]);
  };

  return {
    health,
    runs,
    reports,
    charts,
    outputs,
    isLoading: health.isLoading && runs.isLoading,
    isRefreshing:
      health.isFetching || runs.isFetching || reports.isFetching || charts.isFetching || outputs.isFetching,
    error: health.error || runs.error || reports.error || charts.error || outputs.error,
    refetch,
  };
}
