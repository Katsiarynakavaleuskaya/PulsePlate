// API Key management utilities
// SECURITY NOTE: API keys are stored in plain text in browser storage.
// This is acceptable only for user-provided keys that can be easily rotated.

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

export function setStoredApiKey(key: string, remember: boolean = false): void {
  if (typeof window === 'undefined') return;
  const storage = remember ? localStorage : sessionStorage;
  storage.setItem(API_KEY_STORAGE_KEY, key);
  // Clear from other storage
  const otherStorage = remember ? sessionStorage : localStorage;
  otherStorage.removeItem(API_KEY_STORAGE_KEY);
}

export function clearStoredApiKey(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(API_KEY_STORAGE_KEY);
  sessionStorage.removeItem(API_KEY_STORAGE_KEY);
}
