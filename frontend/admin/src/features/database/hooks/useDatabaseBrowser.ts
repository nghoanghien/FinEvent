import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/shared/utils/api";
import type { DbEntity } from "@/shared/types";

export function useDatabaseRows(entity: DbEntity, query: string, offset: number, limit = 50) {
  return useQuery({
    queryKey: ["db", entity, query, offset, limit],
    queryFn: () => adminApi.dbList(entity, { query, limit, offset }),
  });
}

export function useDatabaseDetail(entity: DbEntity, selectedId: string | null) {
  return useQuery({
    queryKey: ["db-detail", entity, selectedId],
    queryFn: () => adminApi.dbDetail(entity, selectedId || ""),
    enabled: Boolean(selectedId),
  });
}
