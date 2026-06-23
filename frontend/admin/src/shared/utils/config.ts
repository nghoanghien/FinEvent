"use client";

import type { ApiRuntimeConfig } from "../types";

const API_BASE_KEY = "finevent.admin.apiBaseUrl";
const API_KEY_KEY = "finevent.admin.apiKey";

export const DEFAULT_API_BASE_URL =
  process.env.NEXT_PUBLIC_FINEVENT_API_BASE_URL || "http://127.0.0.1:8000";

export function getStoredConfig(): ApiRuntimeConfig {
  if (typeof window === "undefined") {
    return { baseUrl: DEFAULT_API_BASE_URL, adminApiKey: "" };
  }
  const storedBaseUrl = window.localStorage.getItem(API_BASE_KEY);
  const baseUrl =
    storedBaseUrl === "http://127.0.0.1:18000" && DEFAULT_API_BASE_URL !== storedBaseUrl
      ? DEFAULT_API_BASE_URL
      : storedBaseUrl || DEFAULT_API_BASE_URL;
  return {
    baseUrl,
    adminApiKey: window.localStorage.getItem(API_KEY_KEY) || "",
  };
}

export function saveStoredConfig(config: ApiRuntimeConfig) {
  window.localStorage.setItem(API_BASE_KEY, config.baseUrl.trim() || DEFAULT_API_BASE_URL);
  window.localStorage.setItem(API_KEY_KEY, config.adminApiKey.trim());
}

export function clearStoredAdminKey() {
  window.localStorage.removeItem(API_KEY_KEY);
}

export function configStorageKeys() {
  return { apiBaseKey: API_BASE_KEY, apiKeyKey: API_KEY_KEY };
}
