// RU: API клиент с поддержкой аутентификации. Обрабатывает 401 ошибки, перенаправляя на страницу ввода ключа.
// EN: API client with authentication support. Handles 401 errors by redirecting to key entry page.

import { logError } from "../lib/analytics";
import { getStoredApiKey, clearStoredApiKey } from "../auth/storage";

// Allow overriding storage functions for testing
const _getStoredApiKey = (globalThis as any).__TEST_getStoredApiKey__ || getStoredApiKey;
const _clearStoredApiKey = (globalThis as any).__TEST_clearStoredApiKey__ || clearStoredApiKey;

/**
 * Custom error class for 401 Unauthorized responses
 */
export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

// Allow overriding API_BASE for testing
export const API_BASE = (globalThis as any).__TEST_API_BASE__ || ((import.meta as any).env?.VITE_API_BASE || "") as string;

if (!API_BASE && !(globalThis as any).__TEST_API_BASE__) {
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

// API Key management moved to auth context
// Re-export for backward compatibility
export { getStoredApiKey, setStoredApiKey, clearStoredApiKey } from "../auth/storage";

/**
 * Validates API key by making a lightweight request to the backend
 * @returns Promise<boolean> - true if key is valid
 */
export async function validateApiKey(): Promise<boolean> {
  try {
    // Use direct fetch to avoid 401 error handling that clears keys and redirects
    const res = await fetch(`${API_BASE}/health`, {
      method: "GET",
      headers: mergeHeaders(),
    });
    return res.ok;
  } catch (error) {
    return false;
  }
}

function mergeHeaders(init?: RequestInit, forceJson?: boolean): Headers {
  const defaults: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language":
      (typeof navigator !== "undefined" && navigator.language) || "en",
  };

  // Add API key if available
  const apiKey = _getStoredApiKey();
  if (apiKey) {
    defaults["X-API-Key"] = apiKey;
  }

  // Check if caller already provided Content-Type (case-insensitive)
  const hasContentType = (() => {
    if (!init?.headers) {
      return false;
    }

    const incoming = init.headers instanceof Headers
      ? init.headers
      : new Headers(init.headers as HeadersInit);

    // Check for Content-Type header case-insensitively
    for (const [key] of incoming) {
      if (key.toLowerCase() === "content-type") {
        return true;
      }
    }
    return false;
  })();

  // Only set Content-Type if caller didn't provide one
  if (!hasContentType) {
    if (forceJson === true) {
      // Explicit flag takes priority
      defaults["Content-Type"] = "application/json";
    } else if (forceJson === undefined && init?.body && typeof init.body === "string") {
      // Fall back to safe JSON detection only when flag is undefined
      try {
        JSON.parse(init.body.trim());
        defaults["Content-Type"] = "application/json";
      } catch {
        // Not valid JSON, don't set Content-Type
      }
    }
  }

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
 * @param navigate - Optional React Router navigate function for SPA redirects.
 * @param forceJson - Optional flag to explicitly set Content-Type to application/json, bypassing automatic detection.
 * @returns The parsed JSON response typed as `T`.
 * @throws Error when the network request fails with a non-OK response, when no mock is mapped for the path, or when both the network request and mock fallback fail.
 */
async function api<T>(path: string, init?: RequestInit, navigate?: (path: string) => void, forceJson?: boolean): Promise<T> {
  const tryNetwork = async (): Promise<T> => {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: mergeHeaders(init, forceJson),
    });
    if (!res.ok) {
      // Handle 401 Unauthorized - redirect to auth
      if (res.status === 401) {
        // Clear invalid API key
        _clearStoredApiKey();
        // Redirect to enter key page (SPA redirect if navigate provided, otherwise sync location)
        if (navigate) {
          navigate("/enter-key");
        } else if (typeof window !== "undefined") {
          window.location.replace("/enter-key");
        }
        // Throw specific UnauthorizedError so callers can detect 401
        throw new UnauthorizedError("API key invalid or expired.");
      }

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

export { api };
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

/**
 * Calculates Basal Metabolic Rate (BMR) based on user parameters
 * @param body - Request body with user parameters for BMR calculation
 * @param navigate - Optional React Router navigate function for SPA redirects
 * @returns Promise<BmrResponse> - BMR calculation result
 */
export const getBmr = (body: BmrRequest, navigate?: (path: string) => void) =>
  api<BmrResponse>("/premium/bmr", { method: "POST", body: JSON.stringify(body) }, navigate, true);

/**
 * Retrieves personalized nutrition plate recommendations
 * @param navigate - Optional React Router navigate function for SPA redirects
 * @returns Promise<PlateResponse> - Nutrition plate data
 */
export const getPlate = (navigate?: (path: string) => void) => api<PlateResponse>("/premium/plate", undefined, navigate);

/**
 * Generates a weekly meal plan
 * @param navigate - Optional React Router navigate function for SPA redirects
 * @returns Promise<WeekPlanResponse> - Weekly meal plan data
 */
export const getWeekPlan = (navigate?: (path: string) => void) => api<WeekPlanResponse>("/plan/week", undefined, navigate);
