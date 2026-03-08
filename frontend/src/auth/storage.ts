// RU: Legacy API key storage utilities (migration-only).
// EN: Legacy API key storage utilities (migration-only).
//
// SECURITY: Persistent browser storage for auth secrets is deprecated.
// The app now uses server-side session cookies.

const API_KEY_STORAGE_KEY = 'pulseplate_api_key';

function readLegacyApiKey(storage: Storage): string | null {
  try {
    return storage.getItem(API_KEY_STORAGE_KEY);
  } catch {
    return null;
  }
}

/**
 * Retrieves a legacy API key from browser storage for one-time migration only.
 * The value is consumed and cleared immediately to avoid keeping auth secrets in the browser.
 */
export function getStoredApiKey(): string | null {
  if (typeof window === 'undefined') return null;
  const legacyKey = readLegacyApiKey(localStorage) || readLegacyApiKey(sessionStorage);
  if (legacyKey) {
    clearStoredApiKey();
  }
  return legacyKey;
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
  try {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  } catch {
    // Ignore unavailable storage during fail-closed cleanup.
  }
  try {
    sessionStorage.removeItem(API_KEY_STORAGE_KEY);
  } catch {
    // Ignore unavailable storage during fail-closed cleanup.
  }
}
