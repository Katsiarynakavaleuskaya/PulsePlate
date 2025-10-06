// Single source of truth for user settings (including API key).
// SSR/test-safe. Listens to changes across tabs.

import { z } from "zod";
import i18n from "../i18n";

const NS = "pulseplate.settings.v1";
const isBrowser = typeof window !== "undefined" && typeof localStorage !== "undefined";

const SettingsSchema = z.object({
  apiKey: z.string().optional(),
  // зарезервировано: lang, theme, diet_flags, и т.д.
});

type Settings = z.infer<typeof SettingsSchema>;

function read(): Settings {
  if (!isBrowser) return {};
  try {
    const raw = localStorage.getItem(NS);
    if (!raw) return {};

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

function write(next: Settings) {
  if (!isBrowser) return;
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
      const detail = (e as CustomEvent<unknown>).detail;
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
    window.addEventListener("storage", onStorage);
    window.addEventListener("settings:changed", onInTab as EventListener);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("settings:changed", onInTab as EventListener);
    };
  },
};
