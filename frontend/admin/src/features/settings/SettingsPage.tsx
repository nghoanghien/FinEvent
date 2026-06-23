"use client";

import { useQueryClient } from "@tanstack/react-query";
import { KeyRound, Save, Server, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorBlock, LoadingBlock } from "@/components/ui/StateBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { JsonPanel } from "@/components/ui/JsonPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { clearStoredAdminKey, configStorageKeys, DEFAULT_API_BASE_URL, getStoredConfig, saveStoredConfig } from "@/shared/utils/config";
import { useSettingsHealth } from "./hooks/useAdminSettings";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const [baseUrl, setBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [adminApiKey, setAdminApiKey] = useState("");
  const [saved, setSaved] = useState(false);
  const health = useSettingsHealth();

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
    <div className="eatzy-page space-y-8">
      <PageHeader
        eyebrow="Runtime settings"
        title="API SETTINGS"
        icon={KeyRound}
        description="Kết nối Next.js admin với FastAPI. API key lưu trong localStorage trình duyệt để tiện demo local, không commit secret vào source code."
      />

      <section className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <div className="panel p-8">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-100 text-gray-600">
              <KeyRound className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Admin API credentials</h3>
              <p className="text-sm font-medium text-gray-400">Dùng header X-Admin-API-Key cho mọi /admin/* request.</p>
            </div>
          </div>
          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="text-sm font-bold text-gray-700">FastAPI base URL</span>
              <input
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                className="focus-ring mt-2 h-12 w-full rounded-full border border-gray-100 bg-gray-100 px-4 text-sm font-medium text-gray-700"
                placeholder="http://127.0.0.1:8000"
              />
            </label>
            <label className="block">
              <span className="text-sm font-bold text-gray-700">Admin API key</span>
              <input
                value={adminApiKey}
                onChange={(event) => setAdminApiKey(event.target.value)}
                type="password"
                className="focus-ring mt-2 h-12 w-full rounded-full border border-gray-100 bg-gray-100 px-4 text-sm font-medium text-gray-700"
                placeholder="FINEVENT_ADMIN_API_KEY"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={save} className="eatzy-primary-button">
                <Save className="h-4 w-4" />
                Lưu và test health
              </button>
              <button type="button" onClick={clearKey} className="eatzy-secondary-button">
                <Trash2 className="h-4 w-4" />
                Xóa key local
              </button>
            </div>
            {saved ? <p className="text-sm font-semibold text-lime-700">Đã lưu cấu hình local.</p> : null}
          </div>
        </div>

        <div className="panel p-8">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Health check</h3>
              <p className="mt-1 text-sm font-medium text-gray-400">Kiểm tra API, DB, pgvector, model env và artifact dirs.</p>
            </div>
            <Server className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-5">
            {health.isFetching ? <LoadingBlock label="Đang kiểm tra health..." /> : null}
            {health.error ? <ErrorBlock error={health.error} onRetry={() => health.refetch()} /> : null}
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
                    <div key={key} className="flex items-center justify-between rounded-2xl border border-gray-100 bg-gray-50 p-3">
                      <span className="text-sm font-medium text-gray-600">{key}</span>
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

      <section className="panel p-8">
        <h3 className="font-anton text-2xl font-black uppercase text-gray-900">Local storage keys</h3>
        <p className="mt-1 text-sm font-medium text-gray-400">Dùng để debug khi cần xóa tay trong DevTools.</p>
        <div className="mt-5">
          <JsonPanel value={configStorageKeys()} />
        </div>
      </section>
    </div>
  );
}
