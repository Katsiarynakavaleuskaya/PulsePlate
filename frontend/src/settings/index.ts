// Единственная точка правды для пользовательских настроек (включая API-ключ).
// Безопасно для SSR/тестов и синхронизирует изменения между вкладками.

const STORAGE_KEY = "pulseplate.settings.v1";
const hasBrowserApis = typeof window !== "undefined" && typeof localStorage !== "undefined";

export type SettingsSnapshot = {
  apiKey?: string;
  // Резерв под будущие настройки: lang, theme, diet_flags, и т.д.
};

function readSnapshot(): SettingsSnapshot {
  if (!hasBrowserApis) {
    return {};
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SettingsSnapshot) : {};
  } catch {
    return {};
  }
}

function writeSnapshot(next: SettingsSnapshot) {
  if (!hasBrowserApis) {
    return;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    // storage-событие не срабатывает в той же вкладке, поэтому транслируем вручную.
    window.dispatchEvent(new CustomEvent("pulseplate:settings", { detail: next }));
  } catch {
    // Игнорируем quota/security ошибки — fallback остаётся пустым.
  }
}

export const SettingsStore = {
  get(): SettingsSnapshot {
    return readSnapshot();
  },
  set(partial: Partial<SettingsSnapshot>) {
    writeSnapshot({ ...readSnapshot(), ...partial });
  },
  clear() {
    writeSnapshot({});
  },
  getApiKey(): string | undefined {
    return readSnapshot().apiKey;
  },
  setApiKey(apiKey: string) {
    writeSnapshot({ ...readSnapshot(), apiKey });
  },
  clearApiKey() {
    const snapshot = readSnapshot();
    if (snapshot.apiKey !== undefined) {
      delete snapshot.apiKey;
      writeSnapshot(snapshot);
    }
  },
  subscribe(listener: (snapshot: SettingsSnapshot) => void) {
    if (!hasBrowserApis) {
      return () => {};
    }

    const handleStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) {
        listener(readSnapshot());
      }
    };

    const handleCustom = (event: Event) => {
      listener(((event as CustomEvent<SettingsSnapshot>).detail) ?? readSnapshot());
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener("pulseplate:settings", handleCustom as EventListener);

    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("pulseplate:settings", handleCustom as EventListener);
    };
  },
};
