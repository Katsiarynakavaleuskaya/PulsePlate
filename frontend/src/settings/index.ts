// Single source of truth for user settings (including API key).
// SSR/test-safe. Listens to changes across tabs.

import i18n from "../i18n";

const NS = "pulseplate.settings.v1";
const isBrowser = typeof window !== "undefined" && typeof localStorage !== "undefined";

type Settings = {
  apiKey?: string;
  // зарезервировано: lang, theme, diet_flags, и т.д.
};

function read(): Settings {
  if (!isBrowser) return {};
  try {
    const raw = localStorage.getItem(NS);
    return raw ? (JSON.parse(raw) as Settings) : {};
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error("settings.read failed", err);
    }
    return {};
  }
}

function write(next: Settings) {
  if (!isBrowser) return;
  try {
    localStorage.setItem(NS, JSON.stringify(next));
    // Notify current tab (storage event doesn't fire in the same tab)
    window.dispatchEvent(new CustomEvent("settings:changed", { detail: next }));
  } catch (error) {
    // Log error for diagnostics
    if (import.meta.env.DEV) {
      console.error("settings write failed", error);
    }

    // Show user notification for storage-related errors
    if (error instanceof DOMException) {
      if (error.name === "QuotaExceededError") {
        // Ленивый импорт toast для избежания зависимостей
        import("../components/ui").then(({ showError }) => {
          showError(i18n.t("settings.storageQuotaExceeded"));
        }).catch(() => {
          // Если toast недоступен, используем нативный alert как fallback
          alert(i18n.t("settings.storageQuotaExceeded"));
        });
      } else if (error.name === "SecurityError") {
        if (import.meta.env.DEV) {
          console.warn("settings write blocked by security policy", error);
        }
      }
    } else {
      // For other errors (e.g., JSON serialization) just log
      if (import.meta.env.DEV) {
        console.warn("unexpected settings write error", error);
      }
    }
  }
}

export const SettingsStore = {
  get(): Settings { return read(); },
  // Atomic updater: reads current state, applies pure update function,
  // returns new state without mutations, writes result.
  update(fn: (s: Settings) => Settings) { write(fn(read())); },
  set(patch: Partial<Settings>) { this.update(s => ({ ...s, ...patch })); },
  clear() { write({}); },

  getApiKey(): string | undefined { return read().apiKey; },
  setApiKey(k: string) { this.update(s => ({ ...s, apiKey: k })); },
  clearApiKey() { this.update(s => ({ ...s, apiKey: undefined })); },

  // Subscribe to changes from other tabs/windows
  subscribe(fn: (s: Settings) => void) {
    if (!isBrowser) return () => {};
    const onStorage = (e: StorageEvent) => {
      if (e.key === NS) fn(read());
    };
    const onInTab = (e: Event) => {
      const detail = (e as CustomEvent<Settings>).detail;
      if (detail && typeof detail === "object") {
        fn(detail);
      } else {
        fn(read());
      }
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("settings:changed", onInTab as EventListener);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("settings:changed", onInTab as EventListener);
    };
  },
};
