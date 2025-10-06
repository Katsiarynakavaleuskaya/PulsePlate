// RU: Клиент для FastAPI с поддержкой API ключа и моков.
// EN: FastAPI client with API key support and mocks.

import { SettingsStore } from "../settings";
import { logError } from "../lib/analytics";
import { getMockUrl } from "../mocks/config";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

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

const forceMock = searchParams.get("mock") === "1";

function getAutomaticMockUrl(path: string): string | null {
  return getMockUrl(path);
}

type ApiOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  mockUrl?: string;
  forceMock?: boolean;
  onAuthError?: (code: 401 | 403, ctx: { clearApiKey: () => void }) => void;
  credentials?: RequestCredentials;
  signal?: AbortSignal;
};

function buildHeaders(
  apiKey: string | undefined,
  base: Record<string, string> = {},
  hasBody: boolean,
  body?: unknown
) {
  const h: Record<string, string> = { ...base };
function buildHeaders(
  apiKey: string | undefined,
  base: Record<string, string> = {},
  hasBody: boolean
) {
  const h: Record<string, string> = { ...base };
  if (apiKey) h["X-API-Key"] = apiKey;
  // Для GET/без тела не шлём Content-Type

  // Normalize header keys to lowercase for case-insensitive check
  const lowerCaseKeys = Object.keys(h).map((k) => k.toLowerCase());
  if (hasBody && !lowerCaseKeys.includes("content-type")) h["Content-Type"] = "application/json";
  return h;
}

export async function api<T = unknown>(url: string, opts: ApiOptions = {}): Promise<T | undefined> {
  const {
    method = "GET",
    body,
    headers,
    mockUrl,
    forceMock = false,
    onAuthError,
    credentials,
    signal,
  } = opts;

  const apiKey = SettingsStore.getApiKey();
  const hasBody = body !== undefined && method !== "GET";
  const finalHeaders = buildHeaders(apiKey, headers, hasBody, body);

  // Prepare body once - only stringify if it's a plain object/array, leave strings/FormData as-is
  let preparedBody: BodyInit | undefined;
  if (hasBody && body !== undefined) {
    if (
      typeof body === "string" ||
      body instanceof FormData ||
      body instanceof URLSearchParams ||
      body instanceof Blob ||
      body instanceof ArrayBuffer
    ) {
      preparedBody = body;
    } else {
      preparedBody = JSON.stringify(body);
    }
  }

  const primary = `${API_BASE}${url}`;
  const useMock = async () => {
    if (!mockUrl) throw new Error("Mock URL not provided");
    try {
      return await fetch(mockUrl, {
        method,
        headers: finalHeaders,
        body: preparedBody,
        credentials,
        signal,
      });
    } catch (mockErr) {
      try { logError(mockErr); } catch {}
      throw mockErr;
    }
  };

  let res: Response;
  try {
    // Если forceMock — не трогаем сеть
    if (forceMock && mockUrl) {
      res = await useMock();
    } else {
      // Сначала — основной эндпойнт
      res = await fetch(primary, {
        method,
        headers: finalHeaders,
        body: preparedBody,
        credentials,
        signal,
      });
    }
  } catch (netErr) {
    // 🔁 Старое поведение: при сетевой ошибке и наличии mockUrl — фоллбэк
    const automaticMockUrl = getAutomaticMockUrl(url); // Try to get automatic mock URL
    if (!forceMock && (mockUrl || automaticMockUrl)) {
      try { logError(netErr); } catch {}
      // Use explicit mockUrl if provided, otherwise use automatic mockUrl
      const finalMockUrl = mockUrl || automaticMockUrl;
      if (finalMockUrl) {
        const useAutoMock = async () => {
          try {
            return await fetch(finalMockUrl, {
              method,
              headers: finalHeaders,
              body: preparedBody,
              credentials,
              signal,
            });
          } catch (autoMockErr) {
            try { logError(autoMockErr); } catch {}
            throw autoMockErr;
          }
        };
        res = await useAutoMock();
      } else {
        throw netErr;
      }
    } else {
      try { logError(netErr); } catch {}
      throw netErr;
    }
  }

  if (res.status === 401 || res.status === 403) {
    try { logError(new Error(`Auth ${res.status}`)); } catch {}
    onAuthError?.(res.status as 401 | 403, { clearApiKey: SettingsStore.clearApiKey });
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    try { logError(new Error(`HTTP ${res.status}`)); } catch {}
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }

  // Endpoints which may return 204 should call the API with a response type that includes undefined (e.g. api<Response | undefined>(...))
  if (res.status === 204) return undefined;
  return (await res.json()) as T;
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

// Endpoints
export const getBmr = (body: BmrRequest): Promise<BmrResponse | undefined> =>
  api<BmrResponse>("/premium/bmr", { method: "POST", body });

export const getPlate = (): Promise<PlateResponse | undefined> => api<PlateResponse>("/premium/plate");

export const getWeekPlan = (): Promise<WeekPlanResponse | undefined> => api<WeekPlanResponse>("/plan/week");
