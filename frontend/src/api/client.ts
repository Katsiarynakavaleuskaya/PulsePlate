// RU: API клиент с поддержкой серверной cookie-сессии. Обрабатывает 401 ошибки, перенаправляя на страницу входа.
// EN: API client with server-session cookie support. Handles 401 errors by redirecting to key entry page.

import { logError } from "../lib/analytics";
import { clearStoredApiKey } from "../auth/storage";
import type { components } from "./schema";

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
  getStoredApiKey: () => null,
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

/**
 * Normalize API base + path join to avoid duplicate /api or /api/v1 segments.
 *
 * RU: Нормализация join base+path чтобы избежать дублирования /api или /api/v1.
 * EN: Normalize join of base URL and path to avoid duplicate API segments.
 *
 * Examples:
 * - base: "http://localhost:8000/api/v1", path: "/api/v1/x" => "http://localhost:8000/api/v1/x"
 * - base: "http://localhost:8000/api", path: "/api/x" => "http://localhost:8000/api/x"
 * - base: "https://api.test.com", path: "/api/v1/x" => "https://api.test.com/api/v1/x"
 *
 * @param base - API base URL (may include /api or /api/v1)
 * @param apiPath - API path (must start with /api/...)
 * @returns Normalized URL without duplicate segments
 */
export function normalizeApiUrl(base: string, apiPath: string): string {
  // Ensure apiPath starts with /
  const path = apiPath.startsWith('/') ? apiPath : `/${apiPath}`;

  // Parse base URL to get pathname
  let baseUrl: URL;
  try {
    baseUrl = new URL(base);
  } catch {
    // If base is not a valid URL, fall back to naive concat
    return `${base}${path}`;
  }

  const basePath = baseUrl.pathname.replace(/\/+$/, ''); // Strip trailing slashes

  // Deduplicate /api/v1 if both base and path contain it
  // Includes exact match (path === "/api/v1") to handle bare paths
  if (
    basePath.endsWith("/api/v1") &&
    (path === "/api/v1" || path.startsWith("/api/v1/"))
  ) {
    baseUrl.pathname = basePath + path.slice("/api/v1".length);
    return baseUrl.toString();
  }

  // Deduplicate /api if both base and path contain it (but NOT /api/v1 paths)
  // Includes exact match (path === "/api") to handle bare paths
  if (
    basePath.endsWith("/api") &&
    !basePath.endsWith("/api/v1") &&
    (path === "/api" || (path.startsWith("/api/") && !path.startsWith("/api/v1/")))
  ) {
    baseUrl.pathname = basePath + path.slice("/api".length);
    return baseUrl.toString();
  }

  // No duplication - simple concat (ensure no double slashes)
  baseUrl.pathname = basePath + path;
  return baseUrl.toString();
}

const searchParams = (() => {
  if (typeof window === "undefined" || typeof window.location?.search !== "string") {
    return new URLSearchParams();
  }
  return new URLSearchParams(window.location.search);
})();

const forceMock = searchParams.get("mock") === "1";

// PRO nutrition endpoint paths (canonical)
export const PRO_NUTRITION_TARGETS_PATH = "/api/v1/pro/nutrition/targets";
export const PRO_NUTRITION_PLATE_PATH = "/api/v1/pro/nutrition/plate";
export const PRO_SESSION_PATH = "/api/v1/pro/session";
export const PRO_SESSION_EXCHANGE_PATH = "/api/v1/pro/session/exchange";
export const PRO_SESSION_LOGOUT_PATH = "/api/v1/pro/session/logout";

function mockUrl(path: string): string | null {
  if (path.includes("/api/v1/premium/bmr") || path.includes("/premium/bmr")) {
    return "/mock/bmr.json";
  }
  // PRO nutrition endpoints (canonical)
  if (path.includes(PRO_NUTRITION_PLATE_PATH) || path.includes("/pro/nutrition/plate")) {
    return "/mock/plate.json";
  }
  if (path.includes(PRO_NUTRITION_TARGETS_PATH) || path.includes("/pro/nutrition/targets")) {
    return "/mocks/targets.json";
  }
  if (path.includes("/plan/week")) {
    return "/mock/week.json";
  }
  return null;
}

// Legacy API key management exports kept for backward compatibility.
// Browser persistence is disabled in storage.ts.
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
  } catch (error) {
    return false;
  }
}

function inferSessionActive(payload: unknown): boolean {
  if (!payload || typeof payload !== "object") {
    return false;
  }

  const source = payload as Record<string, unknown>;
  const rootBooleanKeys = ["authenticated", "active", "ok", "has_session", "is_authenticated"];
  for (const key of rootBooleanKeys) {
    if (typeof source[key] === "boolean") {
      return source[key] as boolean;
    }
  }

  const nestedSession = source.session;
  if (nestedSession && typeof nestedSession === "object") {
    const nested = nestedSession as Record<string, unknown>;
    for (const key of rootBooleanKeys) {
      if (typeof nested[key] === "boolean") {
        return nested[key] as boolean;
      }
    }
  }

  return false;
}

/**
 * Check whether server-side PRO session is currently active.
 * Auth source of truth for web flow.
 */
export async function checkProSession(): Promise<boolean> {
  try {
    validateApiBase();
    const response = await fetch(normalizeApiUrl(getApiBase(), PRO_SESSION_PATH), {
      method: "GET",
      headers: mergeHeaders(),
      credentials: "include",
    });

    if (response.status === 401 || response.status === 403) {
      return false;
    }
    if (!response.ok) {
      return false;
    }

    const payload = await response.json().catch(() => null);
    return inferSessionActive(payload);
  } catch {
    return false;
  }
}

/**
 * Exchange a legacy API key for a secure server-side session cookie.
 * Returns true only when a valid session is established.
 */
export async function exchangeApiKeyForSession(apiKey: string): Promise<boolean> {
  const trimmedKey = apiKey.trim();
  if (!trimmedKey) {
    return false;
  }

  try {
    validateApiBase();

    const response = await fetch(normalizeApiUrl(getApiBase(), PRO_SESSION_EXCHANGE_PATH), {
      method: "POST",
      headers: mergeHeaders(
        {
          headers: {
            "X-API-Key": trimmedKey,
          },
        },
      ),
      credentials: "include",
    });

    if (response.status === 401 || response.status === 403) {
      return false;
    }
    if (!response.ok) {
      return false;
    }

    const payload = await response.json().catch(() => null);
    return inferSessionActive(payload);
  } catch {
    return false;
  }
}

/**
 * Best-effort server session clear (logout).
 * Errors are intentionally swallowed to keep UX deterministic.
 */
export async function clearProSession(): Promise<void> {
  try {
    validateApiBase();
    await fetch(normalizeApiUrl(getApiBase(), PRO_SESSION_LOGOUT_PATH), {
      method: "POST",
      headers: mergeHeaders(),
      credentials: "include",
    });
  } catch {
    // no-op
  }
}

function mergeHeaders(init?: RequestInit, forceJson?: boolean): Headers {
  const defaults: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language":
      (typeof navigator !== "undefined" && navigator.language) || "en",
  };

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

export async function api<T = unknown>(
  path: string,
  init?: RequestInit & { mockUrl?: string; forceMock?: boolean },
  options?: ApiOptions,
  forceJson?: boolean
): Promise<T> {

  const tryNetwork = async (): Promise<T> => {
    // Validate API base before network request
    validateApiBase();

    /** NOTE: api() automatically serializes plain object/array bodies to JSON for non-GET requests.
     *  Higher layers (createPremiumEndpoint, hooks) should pass body as an object; GET without body must not set Content-Type.
     */
    let serializedBody = init?.body;
    let forceJsonForBody = forceJson;

    // Serialize ONLY plain objects/arrays; keep FormData/Blob/ArrayBuffer/ReadableStream/File/Response/Request AS-IS.
    const body = init?.body as any;
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
      typeof body?.arrayBuffer === "function";

    if (isPlainObjectOrArray && !isForbiddenBinaryLike) {
      serializedBody = JSON.stringify(body);
      forceJsonForBody = true;
    }

    const requestInit = {
      ...init,
      body: serializedBody,
      headers: mergeHeaders({ ...init, body: serializedBody }, forceJsonForBody),
      credentials: init?.credentials ?? 'include',
      signal: init?.signal,
    };

    const res = await fetch(normalizeApiUrl(getApiBase(), path), requestInit);
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
        logError(new UnauthorizedError(`Session invalid or expired (${res.status}).`));
        // Throw specific UnauthorizedError so callers can detect auth errors
        throw new UnauthorizedError(`Session invalid or expired (${res.status}).`);
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

/**
 * Classify URL for fetchBlob() to determine auth behavior
 * RU: Классификация URL для определения поведения аутентификации
 * EN: URL classification to determine authentication behavior
 *
 * - 'api': Internal API path (/api/...) - requires auth headers, base URL prepend
 * - 'absolute': External URL (https://...) - no auth, pass-through
 *
 * @throws Error if URL is invalid (not API path or absolute URL)
 */
function classifyUrl(url: string): 'api' | 'absolute' {
  if (url.startsWith('/api/')) return 'api';
  if (url.startsWith('http://') || url.startsWith('https://')) return 'absolute';
  throw new Error(`Invalid URL for fetchBlob: ${url}. Must be /api/... or absolute URL.`);
}

/**
 * Fetch binary data (Blob) from API or external URL.
 * RU: Загрузка бинарных данных (Blob) из API или внешнего URL.
 * EN: Fetch binary data (Blob) from API or external URL.
 *
 * URL Classification:
 * - `/api/...` (API path): Prepends VITE_API_BASE, includes cookie credentials, handles 401/403
 * - `https://...` (External): Pass-through fetch, NO auth headers (signed URLs have token in query)
 *
 * Security: auth headers are NEVER sent to external URLs to prevent credential leaks.
 *
 * @param url - API path (/api/v1/...) or absolute URL (https://...)
 * @param init - Optional fetch init options
 * @returns Promise<Blob> - Binary data as Blob
 */
export async function fetchBlob(
  url: string,
  init?: RequestInit
): Promise<Blob> {
  const kind = classifyUrl(url);

  // Build final URL and headers based on classification
  // Use normalizeApiUrl to avoid duplicate /api or /api/v1 segments
  const finalUrl = kind === 'api' ? normalizeApiUrl(getApiBase(), url) : url;

  // Only validate API base and add auth for API paths
  if (kind === 'api') {
    validateApiBase();
  }

  // For API paths: include cookies; for external: strip auth headers and omit credentials
  let finalInit: RequestInit;

  if (kind === 'api') {
    finalInit = {
      ...init,
      headers: mergeHeaders(init),
      credentials: init?.credentials ?? 'include',
    };
  } else {
    // Security: never leak auth to external domains
    const sanitized = new Headers(init?.headers as HeadersInit | undefined);
    sanitized.delete('authorization');
    sanitized.delete('Authorization');
    sanitized.delete('x-api-key');
    sanitized.delete('X-API-Key');

    finalInit = {
      ...init,
      headers: sanitized,
      credentials: 'omit',
    };
  }

  const res = await fetch(finalUrl, finalInit);

  if (!res.ok) {
    // Handle 401/403 ONLY for API paths (not external signed URLs)
    if (kind === 'api' && (res.status === 401 || res.status === 403)) {
      _clearStoredApiKey();
      if (typeof window !== 'undefined') {
        window.location.replace('/enter-key');
      }
      const authError = new UnauthorizedError(`Session invalid or expired (${res.status}).`);
      logError(authError);
      throw authError;
    }
    throw new Error(`Fetch blob failed: HTTP ${res.status} for ${url}`);
  }

  return res.blob();
}

export { getBmr, getPlate, getTargets } from "./premium";
export type {
  BmrRequest,
  BmrApiResponse,
  PlateRequest,
  PlateResponse,
  TargetsRequest,
  TargetsApiResponse,
} from "./premium";

// OpenAPI generated types
// NOTE: OpenAPI schema name is WeeklyPlanResponse; keep WeekPlanResponse as a local alias.
export type WeekPlanResponse = components["schemas"]["WeeklyPlanResponse"];

// Endpoints

/**
 * Generates a weekly meal plan
 * @param options - Optional API options for auth error handling
 * @returns Promise<WeekPlanResponse> - Weekly meal plan data
 */
export const getWeekPlan = (options?: ApiOptions) => api<WeekPlanResponse>("/plan/week", undefined, options);
