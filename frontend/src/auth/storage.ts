// RU: Legacy API key storage utilities (migration-only).
// EN: Legacy API key storage utilities (migration-only).
//
// SECURITY: Persistent browser storage for auth secrets is deprecated.
// The app now uses server-side session cookies.

const API_KEY_STORAGE_KEY = 'pulseplate_api_key';

/**
 * Retrieves the stored API key from browser storage.
 * Checks localStorage first and returns if present, otherwise returns sessionStorage.
 * Note: setStoredApiKey clears the other storage when setting to avoid ambiguity.
 */
export function getStoredApiKey(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(API_KEY_STORAGE_KEY) || sessionStorage.getItem(API_KEY_STORAGE_KEY);
}

/**
 * @deprecated
 * RU: Сохранение API-ключа в браузере отключено по security policy.
 * EN: Browser persistence for API keys is disabled by security policy.
 */
export function setStoredApiKey(_key: string, _remember: boolean = false): void {
  if (typeof window === 'undefined') return;
  // Keep behavior deterministic: remove any legacy value instead of persisting new secrets.
  clearStoredApiKey();
}

export function clearStoredApiKey(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(API_KEY_STORAGE_KEY);
  sessionStorage.removeItem(API_KEY_STORAGE_KEY);
}
