import { SettingsStore } from "../settings";

export function getStoredApiKey(): string | null {
  return SettingsStore.getApiKey() ?? null;
}

export function setStoredApiKey(key: string): void {
  SettingsStore.setApiKey(key);
}

export function clearStoredApiKey(): void {
  SettingsStore.clearApiKey();
}
