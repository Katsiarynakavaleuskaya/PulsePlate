import { useAuth } from './auth';

/**
 * Hook for API key management - simplified interface to useAuth
 */
export function useApiKey() {
  const { apiKey, setApiKey, clearApiKey, isAuthenticated } = useAuth();

  return {
    apiKey,
    setApiKey,
    clearApiKey,
    isAuthenticated,
  };
}
