// Единая точка правды для пользовательских настроек (вкл. API-ключ).
// Безопасен для SSR/тестов. Слушает изменения между вкладками.

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
    // уведомим текущую вкладку (storage-событие не срабатывает в той же вкладке)
    window.dispatchEvent(new CustomEvent("settings:changed", { detail: next }));
  } catch (error) {
    // Логируем ошибку для диагностики
    if (import.meta.env.DEV) {
      console.error("settings write failed", error);
    }

    // Показываем пользовательское уведомление для storage-related ошибок
    if (error instanceof DOMException) {
      if (error.name === "QuotaExceededError") {
        // Ленивый импорт toast для избежания зависимостей
        import("../components/ui/Toast").then(({ showError }) => {
          showError("Недостаточно места в хранилище. Очистите кэш браузера или попробуйте позже.");
        }).catch(() => {
          // Если toast недоступен, используем нативный alert как fallback
          alert("Недостаточно места в хранилище для сохранения настроек.");
        });
      } else if (error.name === "SecurityError") {
        if (import.meta.env.DEV) {
          console.warn("settings write blocked by security policy", error);
        }
      }
    } else {
      // Для других ошибок (например, JSON serialization) просто логируем
      if (import.meta.env.DEV) {
        console.warn("unexpected settings write error", error);
      }
    }
  }
}

export const SettingsStore = {
  get(): Settings { return read(); },
  // Атомарный updater: читает текущее состояние, применяет чистую функцию обновления,
  // возвращает новое состояние без мутаций, записывает результат.
  update(fn: (s: Settings) => Settings) { write(fn(read())); },
  set(patch: Partial<Settings>) { this.update(s => ({ ...s, ...patch })); },
  clear() { write({}); },

  getApiKey(): string | undefined { return read().apiKey; },
  setApiKey(k: string) { this.update(s => ({ ...s, apiKey: k })); },
  clearApiKey() { this.update(s => ({ ...s, apiKey: undefined })); },

  // Подписка на изменения из других вкладок/окна
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
