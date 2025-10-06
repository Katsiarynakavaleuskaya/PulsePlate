import { useEffect, useState, useCallback } from "react";
import { SettingsStore } from "./index";

/**
 * React hook for managing API key state with cross-tab synchronization.
 * @returns Object containing apiKey state and setter/clear functions
 */
export function useApiKey() {
  const [apiKey, setApiKeyState] = useState<string | undefined>(SettingsStore.getApiKey());

  useEffect(() => {
    const handleApiKeyChange = (e: Event) => {
      const { detail } = e as CustomEvent<string | undefined>;
      setApiKeyState(detail);
    };

    // Listen for apiKey changes
    window.addEventListener("settings:apiKey:changed", handleApiKeyChange);

    // Also listen for general settings changes in case of cross-tab sync
    const unsubscribe = SettingsStore.subscribe(() => {
      // Refresh apiKey from sessionStorage
      setApiKeyState(SettingsStore.getApiKey());
    });

    return () => {
      window.removeEventListener("settings:apiKey:changed", handleApiKeyChange);
      unsubscribe();
    };
  }, []);

  const setApiKey = useCallback((k: string) => {
    SettingsStore.setApiKey(k);
  }, []);

  const clearApiKey = useCallback(() => {
    SettingsStore.clearApiKey();
  }, []);

  return { apiKey, setApiKey, clearApiKey };
}
