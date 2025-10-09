// RU: API клиент с поддержкой аутентификации. Обрабатывает 401 ошибки, перенаправляя на страницу ввода ключа.
// EN: API client with authentication support. Handles 401 errors by redirecting to key entry page.

import { logError } from "../lib/analytics";
import { getStoredApiKey, clearStoredApiKey } from "../auth/storage";

/**
 * Dependencies for API client that can be injected for testing
 */
export interface ApiClientDependencies {
  getStoredApiKey: () => string | null;
  clearStoredApiKey: () => void;
  apiBase: string;
}

/**
 * Default dependencies using production implementations
 */
const defaultDependencies: ApiClientDependencies = {
  getStoredApiKey,
  clearStoredApiKey,
  apiBase: ((import.meta as any).env?.VITE_API_BASE || "") as string,
};

/**
 * Current injected dependencies (mutable for testing)
 */
let injectedDependencies: ApiClientDependencies | null = null;

/**
 * Cached validation flag to avoid redundant API base validation
 * Set to true after first successful validation
 */
let isApiBaseValidated = false;

/**
 * Get the current dependencies (injected or default)
 */
function getDependencies(): ApiClientDependencies {
  return injectedDependencies || defaultDependencies;
}

/**
 * Set dependencies for testing. Pass null to reset to defaults.
 */
export function setApiClientDependencies(deps: ApiClientDependencies | null): void {
  injectedDependencies = deps;
  // Reset validation cache when dependencies change
  isApiBaseValidated = false;
}

// Extract functions from current dependencies
const _getStoredApiKey = () => getDependencies().getStoredApiKey();
const _clearStoredApiKey = () => getDependencies().clearStoredApiKey();

/**
 * Custom error class for 401 Unauthorized responses
 */
export class UnauthorizedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

// Get API base from injected dependencies (computed dynamically)
export const getApiBase = () => getDependencies().apiBase;

/**
 * Validate API base is set and throw error if not
 * Logs error and throws to prevent silent failures during API calls
 * Called lazily to allow for dependency injection in tests
 * Uses cached validation flag to avoid redundant checks
 */
const validateApiBase = () => {
  // Return early if already validated
  if (isApiBaseValidated) {
    return;
  }

  if (!getApiBase()) {
    const envHint = "VITE_API_BASE is not set. Create frontend/.env from .env.example";
    const error = new Error(envHint);
    logError(error);
    throw error;
  }

  // Cache successful validation to avoid redundant checks
  isApiBaseValidated = true;
};

const searchParams = (() => {
  if (typeof window === "undefined" || typeof window.location?.search !== "string") {
    return new URLSearchParams();
  }
  return new URLSearchParams(window.location.search);
})();

const forceMock = searchParams.get("mock") === "1";

function mockUrl(path: string): string | null {
  if (path.includes("/api/v1/premium/bmr") || path.includes("/premium/bmr")) {
    return "/mock/bmr.json";
  }
  if (path.includes("/api/v1/premium/plate") || path.includes("/premium/plate")) {
    return "/mock/plate.json";
  }
  if (path.includes("/api/v1/premium/targets") || path.includes("/premium/targets")) {
    return "/mocks/targets.json";
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
  // Validate API base on first use
  validateApiBase();

  try {
    // Use direct fetch to avoid 401 error handling that clears keys and redirects
    const res = await fetch(`${getApiBase()}/health`, {
      method: "GET",
      headers: mergeHeaders(),
    });
    return res.ok;
  } catch {
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

  // NOTE: api() сам сериализует body в JSON для методов ≠ GET.
  // Высшим слоям (createPremiumEndpoint, hooks) нужно передавать body как объект.

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

export type ApiOptions = {
  onAuthError?: (code: 401 | 403, helpers: { clearApiKey: () => void }) => void;
};

/**
 * Extended RequestInit that allows plain objects as body (they get JSON serialized)
 */
export interface ApiRequestInit extends Omit<RequestInit, 'body'> {
  body?: BodyInit | Record<string, any> | any[] | null;
  mockUrl?: string;
  forceMock?: boolean;
}

export async function api<T = unknown>(
  path: string,
  init?: ApiRequestInit,
  options?: ApiOptions,
  forceJson?: boolean
): Promise<T> {

  const tryNetwork = async (): Promise<T> => {
    // Validate API base before network request
    validateApiBase();

    /** NOTE: api() automatically serializes plain object/array bodies to JSON for non-GET requests.
     *  Higher layers (createPremiumEndpoint, hooks) should pass body as an object; GET without body must not set Content-Type.
     */
    let serializedBody: BodyInit | null = null;
    let forceJsonForBody = forceJson;

    // Serialize ONLY plain objects/arrays; keep FormData/Blob/ArrayBuffer/ReadableStream/File/Response/Request AS-IS.
    const body = init?.body;
    const isPlainObjectOrArray =
      body &&
      typeof body === "object" &&
      (
        Array.isArray(body) ||
        body?.constructor === Object ||
        Object.prototype.toString.call(body) === "[object Object]" // handles cross-realm & Object.create(null)
      );

    const isForbiddenBinaryLike =
      body instanceof FormData ||
      body instanceof Blob ||
      body instanceof ArrayBuffer ||
      // ReadableStream or any object exposing arrayBuffer() (e.g., File/Response/Request):
      body instanceof ReadableStream ||
      (typeof body === "object" && body !== null && "arrayBuffer" in body && typeof body.arrayBuffer === "function");

    if (isPlainObjectOrArray && !isForbiddenBinaryLike) {
      serializedBody = JSON.stringify(body);
      forceJsonForBody = true;
    } else if (body instanceof FormData || body instanceof Blob || body instanceof ArrayBuffer ||
               body instanceof ReadableStream || body instanceof URLSearchParams ||
               typeof body === "string") {
      serializedBody = body;
    }

    const requestInit: RequestInit = {
      ...init,
      body: serializedBody,
      headers: mergeHeaders({ ...init, body: serializedBody }, forceJsonForBody),
      credentials: init?.credentials ?? 'include',
      signal: init?.signal,
    };

    const res = await fetch(`${getApiBase()}${path}`, requestInit);
    if (!res.ok) {
      // Handle 401/403 Unauthorized - call onAuthError callback or fallback behavior
      if (res.status === 401 || res.status === 403) {
        const errorCode = (res.status === 401 ? 401 : 403) as 401 | 403;
        // Call onAuthError callback if provided
        if (options?.onAuthError) {
          options.onAuthError(errorCode, { clearApiKey: _clearStoredApiKey });
        } else {
          // Fallback behavior: clear key and redirect
          _clearStoredApiKey();
          if (typeof window !== "undefined") {
            window.location.replace("/enter-key");
          }
        }
        // Log the auth error
        logError(new UnauthorizedError(`API key invalid or expired (${res.status}).`));
        // Throw specific UnauthorizedError so callers can detect auth errors
        throw new UnauthorizedError(`API key invalid or expired (${res.status}).`);
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

export const fetchJson = api;
export { getBmr, getPlate, getTargets } from "./premium";
export type {
  BmrRequest,
  BmrApiResponse,
  PlateRequest,
  PlateApiResponse,
  TargetsRequest,
  TargetsApiResponse,
} from "./premium";

// Типы минимальные — ровно чтобы начать (уточним позже из OpenAPI)
export type WeekPlanResponse = {
  days: Array<{ date: string; meals: Array<{ name: string; kcal: number }> }>;
};

// Endpoints

/**
 * Generates a weekly meal plan
 * @param options - Optional API options for auth error handling
 * @returns Promise<WeekPlanResponse> - Weekly meal plan data
 */
export const getWeekPlan = (options?: ApiOptions) => api<WeekPlanResponse>("/plan/week", undefined, options);
