// RU: Минимальный клиент для FastAPI. Без моков и MSW на этом шаге.
// EN: Minimal FastAPI client. No mocks/MSW in this step.

import { logError } from "../lib/analytics";
import { SettingsStore } from "../settings";

export const API_BASE = ((import.meta as any).env?.VITE_API_BASE || "") as string;

if (!API_BASE) {
  const envHint = "VITE_API_BASE is not set. Create frontend/.env from .env.example";
  logError(new Error(envHint));
}

const searchParams = (() => {
  if (typeof window === "undefined" || typeof window.location?.search !== "string") {
    return new URLSearchParams();
  }
  return new URLSearchParams(window.location.search);
})();

const globalForceMock = searchParams.get("mock") === "1";

type ApiRequestInit = RequestInit & {
  mockUrl?: string;
  forceMock?: boolean;
  onAuthError?: (code: 401 | 403, ctx: { clearApiKey: () => void }) => void;
};

function resolveMockUrl(path: string): string | null {
  if (path.includes("/premium/bmr")) {
    return "/mock/bmr.json";
  }
  if (path.includes("/premium/plate")) {
    return "/mock/plate.json";
  }
  if (path.includes("/plan/week")) {
    return "/mock/week.json";
  }
  return null;
}

function buildHeaders(init: RequestInit | undefined, apiKey: string | undefined): Headers {
  const defaults: Record<string, string> = {
    Accept: "application/json",
  };
  if (typeof navigator !== "undefined" && navigator.language) {
    defaults["Accept-Language"] = navigator.language;
  }
  if (apiKey) {
    defaults["X-API-Key"] = apiKey;
  }

  let bodyIsJson = false;
  if (typeof init?.body === "string") {
    try {
      JSON.parse(init.body);
      bodyIsJson = true;
    } catch {
      // Not valid JSON, do not set Content-Type
    }
  }
  if (bodyIsJson && !defaults["Content-Type"]) {
    defaults["Content-Type"] = "application/json";
  }

  const headers = new Headers(defaults);

  if (!init?.headers) {
    return headers;
  }

  const incoming =
    init.headers instanceof Headers
      ? init.headers
      : new Headers(init.headers as HeadersInit);

  incoming.forEach((value, key) => {
    headers.set(key, value);
  });

  return headers;
}

async function runFetch(target: string, init: RequestInit): Promise<Response> {
  return fetch(target, init);
}

export async function api<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { mockUrl, forceMock, onAuthError, ...baseInit } = init;
  const apiKey = SettingsStore.getApiKey();
  const headers = buildHeaders(baseInit, apiKey);
  const requestInit: RequestInit = { ...baseInit, headers };

  const endpoint = `${API_BASE}${path}`;
  const fallbackMockUrl = mockUrl ?? resolveMockUrl(path);
  const shouldForceMock = Boolean(forceMock ?? globalForceMock);

  const fetchMock = async (): Promise<Response> => {
    if (!fallbackMockUrl) {
      throw new Error(`No mock mapped for ${path}`);
    }
    const response = await runFetch(fallbackMockUrl, requestInit);
    console.info(`[API] MOCK fallback ON → ${fallbackMockUrl}`);
    return response;
  };

  let res: Response;
  try {
    if (shouldForceMock) {
      res = await fetchMock();
    } else {
      res = await runFetch(endpoint, requestInit);
    }
  } catch (networkError) {
    if (!shouldForceMock && fallbackMockUrl) {
      try {
        logError(networkError, { url: path, endpoint, phase: "network-fallback" });
      } catch {
        // telemetry best-effort
      }
      res = await fetchMock();
    } else {
      try {
        logError(networkError, { url: path, endpoint, phase: "network-error" });
      } catch {
        // ignore
      }
      throw networkError;
    }
  }

  const effectiveUrl = res.url || (shouldForceMock && fallbackMockUrl ? fallbackMockUrl : endpoint);

  if (res.status === 401 || res.status === 403) {
    try {
      logError(new Error(`Auth ${res.status}`), { url: path, endpoint: effectiveUrl });
    } catch {
      // ignore logging errors
    }
    onAuthError?.(res.status as 401 | 403, { clearApiKey: SettingsStore.clearApiKey });
  }

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "<response body unavailable>");
    try {
      logError(new Error(`HTTP ${res.status}`), { url: path, endpoint: effectiveUrl, body: errorBody });
    } catch {
      // ignore logging errors
    }
    throw new Error(`API ${path} failed: HTTP ${res.status}\nResponse body: ${errorBody}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const fetchJson = api;

// Типы минимальные — ровно чтобы начать (уточним позже из OpenAPI)
export type BmrRequest = {
  sex: "male" | "female";
  age: number; // years
  height: number; // cm
  weight: number; // kg
};

export type BmrResponse = {
  bmr: number; // kcal/day
  method: string; // e.g., "Mifflin-St Jeor"
};

export type PlateResponse = {
  calories: number;
  macros: { protein: number; fat: number; carbs: number }; // grams
  micros?: Record<string, number>; // optional micronutrients map
};

export type WeekPlanResponse = {
  days: Array<{ date: string; meals: Array<{ name: string; kcal: number }> }>;
};

export type RagStatsResponse = {
  enabled: boolean;
  stats?: {
    total_chunks: number;
    sources: Record<string, number>;
    index_loaded: boolean;
  };
  error?: string;
};

// Endpoints
export const getBmr = (body: BmrRequest) =>
  api<BmrResponse>("/premium/bmr", { method: "POST", body: JSON.stringify(body) });

export const getPlate = () => api<PlateResponse>("/premium/plate");

export const getWeekPlan = () => api<WeekPlanResponse>("/plan/week");

export const getRagStats = () => api<RagStatsResponse>("/api/v1/rag/stats");

export const toggleRag = (enabled: boolean) =>
  api<{ success: boolean; enabled: boolean }>("/api/v1/rag/toggle", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
