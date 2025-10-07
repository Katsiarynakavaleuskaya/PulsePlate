import { useCallback, useEffect, useState } from "react";
import { SettingsStore, type SettingsSnapshot } from "./index";

export function useApiKey() {
  const [snapshot, setSnapshot] = useState<SettingsSnapshot>(() => SettingsStore.get());

  useEffect(() => {
    return SettingsStore.subscribe(setSnapshot);
  }, []);

  const setApiKey = useCallback((apiKey: string) => {
    SettingsStore.setApiKey(apiKey);
  }, []);

  const clearApiKey = useCallback(() => {
    SettingsStore.clearApiKey();
  }, []);

  return {
    apiKey: snapshot.apiKey,
    setApiKey,
    clearApiKey,
  } as const;
}
