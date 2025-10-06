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
  } catch {
    return {};
  }
}

function write(next: Settings) {
  if (!isBrowser) return;
  try {
    localStorage.setItem(NS, JSON.stringify(next));
    // уведомим текущую вкладку (storage-событие не срабатывает в той же вкладке)
    window.dispatchEvent(new CustomEvent("settings:changed", { detail: next }));
  } catch {}
}

export const SettingsStore = {
  get(): Settings { return read(); },
  set(patch: Partial<Settings>) { write({ ...read(), ...patch }); },
  clear() { write({}); },

  getApiKey(): string | undefined { return read().apiKey; },
  setApiKey(k: string) { write({ ...read(), apiKey: k }); },
  clearApiKey() { const s = read(); delete s.apiKey; write(s); },

  // Подписка на изменения из других вкладок/окна
  subscribe(fn: (s: Settings) => void) {
    if (!isBrowser) return () => {};
    const onStorage = (e: StorageEvent) => {
      if (e.key === NS) fn(read());
    };
    const onInTab = (e: Event) => fn((e as CustomEvent<Settings>).detail ?? read());
    window.addEventListener("storage", onStorage);
    window.addEventListener("settings:changed", onInTab as EventListener);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("settings:changed", onInTab as EventListener);
    };
  },
};
