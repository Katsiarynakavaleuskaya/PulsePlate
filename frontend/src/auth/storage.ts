// RU: Legacy API key storage utilities (migration-only).
// EN: Legacy API key storage utilities (migration-only).
//
// SECURITY: Persistent browser storage for auth secrets is deprecated.
// The app now uses server-side session cookies.

const API_KEY_STORAGE_KEY = 'pulseplate_api_key';
let legacyApiKeyConsumed = false;

function getBrowserStorage(storageKey: 'localStorage' | 'sessionStorage'): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window[storageKey];
  } catch {
    return null;
  }
}

function readLegacyApiKey(storage: Storage | null): string | null {
  if (!storage) return null;
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
  if (legacyApiKeyConsumed) return null;

  const legacyKey =
    readLegacyApiKey(getBrowserStorage('localStorage')) ||
    readLegacyApiKey(getBrowserStorage('sessionStorage'));
  if (legacyKey) {
    // RU: Даже если очистка недоступна, не переэкспонируем legacy secret повторно.
    // EN: Prevent repeated legacy secret exposure even when cleanup is unavailable.
    legacyApiKeyConsumed = true;
    return clearLegacyApiKey() ? legacyKey : null;
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

function clearLegacyApiKey(): boolean {
  if (typeof window === 'undefined') return true;
  const localStorageRef = getBrowserStorage('localStorage');
  const sessionStorageRef = getBrowserStorage('sessionStorage');
  let clearSucceeded = true;
  try {
    localStorageRef?.removeItem(API_KEY_STORAGE_KEY);
  } catch {
    // Ignore unavailable storage during fail-closed cleanup.
    clearSucceeded = false;
  }
  try {
    sessionStorageRef?.removeItem(API_KEY_STORAGE_KEY);
  } catch {
    // Ignore unavailable storage during fail-closed cleanup.
    clearSucceeded = false;
  }
  return clearSucceeded;
}

export function clearStoredApiKey(): void {
  void clearLegacyApiKey();
}
