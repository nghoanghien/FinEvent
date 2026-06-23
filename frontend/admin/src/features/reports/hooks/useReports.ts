import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";

export function useReports(kind: string, limit = 300) {
  return useQuery({
    queryKey: ["reports", kind, limit],
    queryFn: () => adminApi.reports({ kind: kind === "all" ? undefined : kind, limit }),
  });
}

export function useCharts() {
  return useQuery({ queryKey: ["charts"], queryFn: adminApi.charts });
}

export function useReportContent(path: string) {
  return useQuery({
    queryKey: ["report-content", path],
    queryFn: () => adminApi.reportContent(path),
  });
}

export function useReportTable(path: string, limit = 200) {
  return useQuery({
    queryKey: ["report-table", path, limit],
    queryFn: () => adminApi.reportTable(path, { limit }),
  });
}

export function useReportJsonl(path: string, limit = 100) {
  return useQuery({
    queryKey: ["report-jsonl", path, limit],
    queryFn: () => adminApi.reportJsonl(path, { limit }),
  });
}
