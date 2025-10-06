import { useEffect, useState, useCallback } from "react";
import { SettingsStore } from "./index";

export function useApiKey() {
  const [apiKey, setApiKeyState] = useState<string | undefined>(SettingsStore.getApiKey());

  useEffect(() => {
    // Return the unsubscribe function to avoid listener leaks
    return SettingsStore.subscribe((s) => setApiKeyState(s.apiKey));
  }, []);

  const setApiKey = useCallback((k: string) => {
    SettingsStore.setApiKey(k);
  }, []);

  const clearApiKey = useCallback(() => {
    SettingsStore.clearApiKey();
  }, []);

  return { apiKey, setApiKey, clearApiKey };
}
