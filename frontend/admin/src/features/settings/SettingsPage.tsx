"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Save, Server, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { adminApi } from "@/lib/admin-api";
import { clearStoredAdminKey, configStorageKeys, DEFAULT_API_BASE_URL, getStoredConfig, saveStoredConfig } from "@/lib/config";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [baseUrl, setBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [adminApiKey, setAdminApiKey] = useState("");
  const [saved, setSaved] = useState(false);
  const health = useQuery({
    queryKey: ["admin-health", "settings"],
    queryFn: adminApi.health,
  });

  useEffect(() => {
    const config = getStoredConfig();
    setBaseUrl(config.baseUrl);
    setAdminApiKey(config.adminApiKey);
  }, []);

  async function save() {
    saveStoredConfig({ baseUrl, adminApiKey });
    setSaved(true);
    await queryClient.invalidateQueries();
    await health.refetch();
    window.setTimeout(() => setSaved(false), 1600);
  }

  async function clearKey() {
    clearStoredAdminKey();
    setAdminApiKey("");
    await queryClient.invalidateQueries();
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-brand-700">Runtime settings</p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950">Kết nối Next.js admin với FastAPI</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          API key được lưu trong localStorage trình duyệt để tiện demo local. Không commit secret vào source code.
        </p>
      </div>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="panel p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-2">
              <KeyRound className="h-5 w-5 text-slate-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Admin API credentials</h3>
              <p className="text-sm text-slate-500">Dùng header `X-Admin-API-Key` cho mọi `/admin/*` request.</p>
            </div>
          </div>
          <div className="mt-5 space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-slate-700">FastAPI base URL</span>
              <input
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                className="focus-ring mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                placeholder="http://127.0.0.1:8000"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-slate-700">Admin API key</span>
              <input
                value={adminApiKey}
                onChange={(event) => setAdminApiKey(event.target.value)}
                type="password"
                className="focus-ring mt-1 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm"
                placeholder="FINEVENT_ADMIN_API_KEY"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={save}
                className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white"
              >
                <Save className="h-4 w-4" />
                Lưu và test health
              </button>
              <button
                type="button"
                onClick={clearKey}
                className="focus-ring inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
              >
                <Trash2 className="h-4 w-4" />
                Xóa key local
              </button>
            </div>
            {saved ? <p className="text-sm text-emerald-700">Đã lưu cấu hình local.</p> : null}
          </div>
        </div>

        <div className="panel p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-950">Health check</h3>
              <p className="mt-1 text-sm text-slate-500">Kiểm tra API, DB, pgvector, model env và artifact dirs.</p>
            </div>
            <Server className="h-5 w-5 text-slate-400" />
          </div>
          <div className="mt-4">
            {health.isFetching ? <LoadingBlock label="Đang kiểm tra health..." /> : null}
            {health.error ? <ErrorBlock error={health.error} /> : null}
            {health.data ? (
              <div className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  {Object.entries({
                    api: health.data.api,
                    postgres: health.data.postgres,
                    pgvector: health.data.pgvector,
                    teacher_llm: health.data.teacher_llm,
                    student_llm: health.data.student_llm,
                    embedding: health.data.embedding,
                  }).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                      <span className="text-sm text-slate-600">{key}</span>
                      <StatusBadge value={value} />
                    </div>
                  ))}
                </div>
                <JsonPanel value={health.data.artifacts} />
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <section className="panel p-5">
        <h3 className="text-sm font-semibold text-slate-950">Local storage keys</h3>
        <p className="mt-1 text-sm text-slate-500">
          Dùng để debug khi cần xóa tay trong DevTools.
        </p>
        <div className="mt-4">
          <JsonPanel value={configStorageKeys()} />
        </div>
      </section>
    </div>
  );
}
