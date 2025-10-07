import { logError } from "../lib/analytics";
import { SettingsStore } from "../settings";

type AuthErrorHandler = (code: 401 | 403) => void;

type ApiOptions = RequestInit & {
  mockUrl?: string;
  forceMock?: boolean;
  onAuthError?: AuthErrorHandler;
};

export interface ApiClientDependencies {
  getApiKey: () => string | undefined;
  clearApiKey: () => void;
  apiBase: string;
}

const defaultDependencies: ApiClientDependencies = {
  getApiKey: () => SettingsStore.getApiKey(),
  clearApiKey: () => SettingsStore.clearApiKey(),
  apiBase: ((import.meta as any).env?.VITE_API_BASE || "") as string,
};

let injectedDependencies: ApiClientDependencies | null = null;
let apiBaseValidated = false;

const searchParams = (() => {
  if (typeof window === "undefined" || typeof window.location?.search !== "string") {
    return new URLSearchParams();
  }
  return new URLSearchParams(window.location.search);
})();

const globalForceMock = searchParams.get("mock") === "1";

export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnauthorizedError";
  }
}

function getDependencies(): ApiClientDependencies {
  return injectedDependencies ?? defaultDependencies;
}

export const getApiBase = () => getDependencies().apiBase;

export function setApiClientDependencies(deps: ApiClientDependencies | null) {
  injectedDependencies = deps;
  apiBaseValidated = false;
}

function validateApiBase() {
  if (apiBaseValidated) {
    return;
  }

  if (!getDependencies().apiBase) {
    const envHint = "VITE_API_BASE is not set. Create frontend/.env from .env.example";
    const error = new Error(envHint);
    logError(error);
    throw error;
  }

  apiBaseValidated = true;
}

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

function attachContentType(headers: Headers, options?: RequestInit) {
  const hasContentType = Array.from(headers.keys()).some(
    (key) => key.toLowerCase() === "content-type"
  );

  if (hasContentType) {
    return;
  }

  if (options?.body && typeof options.body === "string") {
    try {
      JSON.parse(options.body.trim());
      headers.set("Content-Type", "application/json");
    } catch {
      // ignore
    }
  }
}

function buildHeaders(options?: RequestInit): Headers {
  const defaults: Record<string, string> = {
    Accept: "application/json",
  };

  if (typeof navigator !== "undefined" && navigator.language) {
    defaults["Accept-Language"] = navigator.language;
  }

  const apiKey = getDependencies().getApiKey();
  if (apiKey) {
    defaults["X-API-Key"] = apiKey;
  }

  const headers = new Headers(defaults);

  if (options?.headers) {
    const incoming =
      options.headers instanceof Headers
        ? options.headers
        : new Headers(options.headers as HeadersInit);

    incoming.forEach((value, key) => {
      headers.set(key, value);
    });
  }

  attachContentType(headers, options);
  return headers;
}

async function fetchJsonInternal<T>(path: string, options: ApiOptions = {}): Promise<T> {
  validateApiBase();
  const { onAuthError, mockUrl, forceMock, ...init } = options;
  const dependencies = getDependencies();
  const headers = buildHeaders(init);
  const fallbackMockUrl = mockUrl ?? resolveMockUrl(path);
  const shouldForceMock = Boolean((forceMock ?? false) || (globalForceMock && fallbackMockUrl));

  const tryMock = async () => {
    if (!fallbackMockUrl) {
      throw new Error(`No mock mapped for ${path}`);
    }
    const res = await fetch(fallbackMockUrl, { ...init, headers });
    if (!res.ok) {
      throw new Error(`Mock ${fallbackMockUrl} failed: HTTP ${res.status}`);
    }
    console.info(`[API] MOCK fallback ON → ${fallbackMockUrl}`);
    if (res.status === 204) {
      return undefined as T;
    }
    return (await res.json()) as T;
  };

  const tryNetwork = async () => {
    const endpoint = `${dependencies.apiBase}${path}`;
    const res = await fetch(endpoint, { ...init, headers });

    if (res.status === 401 || res.status === 403) {
      dependencies.clearApiKey();
      onAuthError?.(res.status as 401 | 403);
      if (typeof window !== "undefined") {
        window.location.replace("/enter-key");
      }
      throw new UnauthorizedError("API key invalid or expired.");
    }

    if (!res.ok) {
      const errorBody = await res.text().catch(() => "<response body unavailable>");
      throw new Error(`API ${path} failed: HTTP ${res.status}\nResponse body: ${errorBody}`);
    }

    if (res.status === 204) {
      return undefined as T;
    }

    return (await res.json()) as T;
  };

  if (shouldForceMock) {
    return tryMock();
  }

  try {
    return await tryNetwork();
  } catch (error) {
    if (fallbackMockUrl) {
      try {
        return await tryMock();
      } catch (mockError) {
        throw mockError;
      }
    }
    throw error;
  }
}

export async function api<T>(path: string, options?: ApiOptions): Promise<T> {
  return fetchJsonInternal<T>(path, options);
}

export const fetchJson = api;

export async function validateApiKey(): Promise<boolean> {
  try {
    const dependencies = getDependencies();
    validateApiBase();
    const res = await fetch(`${dependencies.apiBase}/health`, {
      method: "GET",
      headers: buildHeaders(),
    });
    return res.ok;
  } catch {
    return false;
  }
}

type WeekPlanResponse = {
  days: Array<{ date: string; meals: Array<{ name: string; kcal: number }> }>;
};

export const isJsonString = (input: unknown): input is string =>
  typeof input === "string" && (() => {
    try {
      JSON.parse(input.trim());
      return true;
    } catch {
      return false;
    }
  })();

export type BmrRequest = {
  sex: "male" | "female";
  age: number;
  height: number;
  weight: number;
};

export type BmrResponse = {
  bmr: number;
  method: string;
};

export type PlateResponse = {
  calories: number;
  macros: { protein: number; fat: number; carbs: number };
  micros?: Record<string, number>;
};

export type WeekPlanResponse = {
  days: Array<{ date: string; meals: Array<{ name: string; kcal: number }> }>;
};

export const getBmr = (body: BmrRequest) =>
  api<BmrResponse>("/premium/bmr", { method: "POST", body: JSON.stringify(body) });

export const getPlate = () => api<PlateResponse>("/premium/plate");

export const getWeekPlan = (onAuthError?: AuthErrorHandler) =>
  api<WeekPlanResponse>("/plan/week", { onAuthError });
