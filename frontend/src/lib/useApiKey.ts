import { useAuth } from './auth';

/**
 * Hook for API key/session management.
 *
 * Compatibility note:
 * - `setApiKey`/`clearApiKey` keep legacy fire-and-forget behavior for older callers.
 * - Async variants are exposed for new flows that need explicit error handling.
 */
export function useApiKey() {
  const {
    apiKey,
    setApiKey: setApiKeyAsync,
    clearApiKey: clearApiKeyAsync,
    isAuthenticated,
  } = useAuth();

  const setApiKey = (key: string, remember?: boolean): void => {
    void setApiKeyAsync(key, remember).catch(() => {});
  };

  const clearApiKey = (): void => {
    void clearApiKeyAsync().catch(() => {});
  };

  return {
    apiKey,
    setApiKey,
    clearApiKey,
    setApiKeyAsync,
    clearApiKeyAsync,
    isAuthenticated,
  };
}
