// RU: Минимальный клиент для FastAPI. Без моков и MSW на этом шаге.
// EN: Minimal FastAPI client. No mocks/MSW in this step.

import { logError } from "../lib/analytics";

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

const forceMock = searchParams.get("mock") === "1";

function mockUrl(path: string): string | null {
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

function mergeHeaders(init?: RequestInit): Headers {
  const defaults = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "Accept-Language":
      (typeof navigator !== "undefined" && navigator.language) || "en",
  } satisfies Record<string, string>;

  const headers = new Headers(defaults);

  if (!init?.headers) {
    return headers;
  }

  const incoming = init.headers instanceof Headers
    ? init.headers
    : new Headers(init.headers as HeadersInit);

  incoming.forEach((value, key) => {
    headers.set(key, value);
  });

  return headers;
}

/**
 * Performs a fetch to the given API path and returns the parsed JSON, using a mock response when mocking is forced or the network request fails.
 *
 * @param path - The endpoint path relative to the configured API base (e.g., "/premium/bmr").
 * @param init - Optional fetch init options to apply to the network request; request headers are merged with defaults.
 * @returns The parsed JSON response typed as `T`.
 * @throws Error when the network request fails with a non-OK response, when no mock is mapped for the path, or when both the network request and mock fallback fail.
 */
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const tryNetwork = async (): Promise<T> => {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: mergeHeaders(init),
    });
    if (!res.ok) {
      const errorBody = await res.text().catch(() => "<response body unavailable>");
      throw new Error(`API ${path} failed: HTTP ${res.status}\nResponse body: ${errorBody}`);
    }
    return res.json() as Promise<T>;
  };

  const tryMock = async (): Promise<T> => {
    const url = mockUrl(path);
    if (!url) {
      throw new Error(`No mock mapped for ${path}`);
    }
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Mock ${url} failed: HTTP ${res.status}`);
    }
        console.info(`[API] MOCK fallback ON → ${url}`);
    return res.json() as Promise<T>;
  };

  if (forceMock) {
    return tryMock();
  }

  try {
    return await tryNetwork();
  } catch (networkError) {
    try {
      return await tryMock();
    } catch (mockError) {
      throw networkError instanceof Error ? networkError : mockError;
    }
  }
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
export const getBmr = (body: BmrRequest) =>
  api<BmrResponse>("/premium/bmr", { method: "POST", body: JSON.stringify(body) });

export const getPlate = () => api<PlateResponse>("/premium/plate");

export const getWeekPlan = () => api<WeekPlanResponse>("/plan/week");
