// Single source of truth for user settings (including API key).
// SSR/test-safe. Listens to changes across tabs.

import { z } from "zod";
import i18n from "../i18n";

const NS = "pulseplate.settings.v1";
const isBrowser = typeof window !== "undefined" && typeof localStorage !== "undefined";

const SettingsSchema = z.object({
  // зарезервировано: lang, theme, diet_flags, и т.д.
  // Note: apiKey is handled separately in sessionStorage to avoid XSS risks with persistent storage
});

type Settings = z.infer<typeof SettingsSchema>;

/**
 * Reads settings from localStorage with validation.
 * @returns Parsed and validated settings object, or empty object on error
 */
function read(): Settings {
  if (!isBrowser) {
    return {};
  }
  try {
    const raw = localStorage.getItem(NS);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw);
    const result = SettingsSchema.safeParse(parsed);

    if (result.success) {
      return result.data;
    } else {
      // Validation failed, return safe default and log in dev
      if (import.meta.env.DEV) {
        console.error("settings.read validation failed", result.error);
      }
      return {};
    }
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error("settings.read failed", err);
    }
    return {};
  }
}

/**
 * Writes validated settings to localStorage and notifies listeners.
 * @param next - Settings object to write
 */
function write(next: Settings) {
  if (!isBrowser) {
    return;
  }
  try {
    // Validate and strip unknown keys before writing
    const validated = SettingsSchema.strip().parse(next);
    localStorage.setItem(NS, JSON.stringify(validated));
    // Notify current tab (storage event doesn't fire in the same tab)
    window.dispatchEvent(new CustomEvent("settings:changed", { detail: validated }));
  } catch (error) {
    // Handle validation errors specifically
    if (error instanceof z.ZodError) {
      if (import.meta.env.DEV) {
        console.error("settings write validation failed, corrupt data not written", error);
      }
      return; // Don't write invalid data
    }

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
  /**
   * Gets current settings from localStorage.
   * @returns Current validated settings
   */
  get(): Settings { return read(); },

  /**
   * Atomic updater: reads current state, applies pure update function,
   * returns new state without mutations, writes result.
   * @param fn - Pure function that takes current settings and returns new settings
   */
  update(fn: (s: Settings) => Settings) { write(fn(read())); },

  /**
   * Merges partial settings into current settings.
   * @param patch - Partial settings object to merge
   */
  set(patch: Partial<Settings>) { this.update(s => ({ ...s, ...patch })); },

  /**
   * Clears all settings from localStorage.
   */
  clear() { write({}); },

  /**
   * Gets API key from sessionStorage.
   * @returns API key string or undefined if not set
   */
  getApiKey(): string | undefined {
    if (!isBrowser || !sessionStorage) {
      return undefined;
    }
    try {
      const stored = sessionStorage.getItem(`${NS}.apiKey`);
      return stored || undefined;
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("settings.getApiKey failed", err);
      }
      return undefined;
    }
  },
  /**
   * Sets API key in sessionStorage and notifies listeners.
   * @param k - API key string to store
   */
  setApiKey(k: string) {
    if (!isBrowser || !sessionStorage) {
      return;
    }
    try {
      sessionStorage.setItem(`${NS}.apiKey`, k);
      // Notify current tab (sessionStorage doesn't fire storage events)
      window.dispatchEvent(new CustomEvent("settings:apiKey:changed", { detail: k }));
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error("settings.setApiKey failed", error);
      }
    }
  },

  /**
   * Clears API key from sessionStorage and notifies listeners.
   */
  clearApiKey() {
    if (!isBrowser || !sessionStorage) {
      return;
    }
    try {
      sessionStorage.removeItem(`${NS}.apiKey`);
      // Notify current tab
      window.dispatchEvent(new CustomEvent("settings:apiKey:changed", { detail: undefined }));
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error("settings.clearApiKey failed", error);
      }
    }
  },

  /**
   * Subscribes to settings changes from other tabs/windows.
   * @param fn - Callback function called when settings change
   * @returns Cleanup function to remove the listener
   */
  subscribe(fn: (s: Settings) => void) {
    if (!isBrowser) {
      return () => {};
    }
    const onStorage = (e: StorageEvent) => {
      if (e.key === NS) {
        fn(read());
      }
    };
    const onInTab = (e: Event) => {
      const { detail } = e as CustomEvent<unknown>;
      if (detail) {
        try {
          const validated = SettingsSchema.parse(detail);
          fn(validated);
        } catch (error) {
          fn(read());
        }
      } else {
        fn(read());
      }
    };
    const onApiKeyChange = () => {
      // ApiKey changes don't affect the main settings object, but trigger a re-read
      // in case components need to refresh their state
      fn(read());
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("settings:changed", onInTab as EventListener);
    window.addEventListener("settings:apiKey:changed", onApiKeyChange);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("settings:changed", onInTab as EventListener);
      window.removeEventListener("settings:apiKey:changed", onApiKeyChange);
    };
  },
};
