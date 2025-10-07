const STORAGE_KEY = "pulseplate.settings.v1";
const hasBrowserApis = typeof window !== "undefined" && typeof window.localStorage !== "undefined";

type SettingsSnapshot = {
  apiKey?: string;
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
    window.dispatchEvent(
      new CustomEvent<SettingsSnapshot>("pulseplate:settings", { detail: next })
    );
  } catch {
    // ignore quota/security errors
  }
}

export const SettingsStore = {
  get(): SettingsSnapshot {
    return readSnapshot();
  },
  set(patch: Partial<SettingsSnapshot>) {
    writeSnapshot({ ...readSnapshot(), ...patch });
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
      const detail = (event as CustomEvent<SettingsSnapshot>).detail;
      listener(detail ?? readSnapshot());
    };

    window.addEventListener("storage", handleStorage);
    window.addEventListener(
      "pulseplate:settings",
      handleCustom as EventListener
    );

    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener(
        "pulseplate:settings",
        handleCustom as EventListener
      );
    };
  },
};

export type { SettingsSnapshot };
