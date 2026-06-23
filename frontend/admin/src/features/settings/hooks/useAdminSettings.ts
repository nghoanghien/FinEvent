import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/shared/utils/api";

export function useSettingsHealth() {
  return useQuery({
    queryKey: ["admin-health", "settings"],
    queryFn: adminApi.health,
  });
}
