"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Circle, RefreshCw } from "lucide-react";
import { adminApi } from "@/shared/utils/api";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function Topbar() {
  const router = useRouter();
  const health = useQuery({
    queryKey: ["admin-health-topbar"],
    queryFn: adminApi.health,
    refetchInterval: 60_000,
  });

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="flex h-16 items-center justify-between gap-4 px-4 lg:px-8">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">FinEvent-VN</p>
          <h1 className="truncate text-base font-semibold text-slate-950">
            Admin vận hành workflow trích xuất sự kiện tài chính
          </h1>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <StatusBadge value={health.data?.api || (health.isError ? "error" : "checking")} />
          <button
            type="button"
            onClick={() => health.refetch()}
            className="focus-ring inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <div
            onClick={() => router.push("/admin/settings")}
            className="focus-ring hidden h-9 cursor-pointer items-center gap-2 rounded-lg bg-slate-950 px-3 text-sm font-medium text-white hover:bg-slate-800 sm:inline-flex"
          >
            <Circle className="h-3 w-3 fill-brand-500 text-brand-500" />
            API settings
          </div>
        </div>
      </div>
    </header>
  );
}
