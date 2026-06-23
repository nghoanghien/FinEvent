import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/admin-api";

export function useOutputsList(articleId: string) {
  return useQuery({
    queryKey: ["outputs", articleId],
    queryFn: () => adminApi.outputs({ article_id: articleId || undefined, limit: 50 }),
  });
}

export function useOutputDetail(selectedRunId: string | null) {
  return useQuery({
    queryKey: ["output-detail", selectedRunId],
    queryFn: () => adminApi.output(selectedRunId || ""),
    enabled: Boolean(selectedRunId),
  });
}

export function useOutputByArticle(articleId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["output-by-article", articleId],
    queryFn: () => adminApi.outputByArticle(articleId),
    enabled,
  });
}
