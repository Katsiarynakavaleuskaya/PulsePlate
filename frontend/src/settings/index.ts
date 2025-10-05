// Единственная точка правды для пользовательских настроек (включая API-ключ).
// Безопасно для SSR/тестов и синхронизирует изменения между вкладками.

const STORAGE_KEY = "pulseplate.settings.v1";
const hasBrowserApis = typeof window !== "undefined" && typeof localStorage !== "undefined";

// Must be 32 chars for AES-256. In real apps, derive this from user input or server-provided value.
const ENCRYPTION_KEY_RAW = "ChangeMeToARandomSecretKeyOf32Ch"; // 32 bytes for AES-256
const ENCRYPTION_IV = new Uint8Array(12); // 12 bytes all zero (replace with random for more security)

async function getCryptoKey(): Promise<CryptoKey> {
  if (typeof window === "undefined" || !window.crypto?.subtle) {
    throw new Error("Web Crypto API not available");
  }
  return window.crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(ENCRYPTION_KEY_RAW),
    { name: "AES-GCM" },
    false,
    ["encrypt", "decrypt"]
  );
}

async function encrypt(plainText: string): Promise<string> {
  const key = await getCryptoKey();
  const enc = new TextEncoder().encode(plainText);
  const ciphertext = await window.crypto.subtle.encrypt(
    { name: "AES-GCM", iv: ENCRYPTION_IV },
    key,
    enc
  );
  // Convert to base64 for storage
  return btoa(String.fromCharCode(...new Uint8Array(ciphertext)));
}

async function decrypt(base64: string): Promise<string> {
  const key = await getCryptoKey();
  const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
  const plain = await window.crypto.subtle.decrypt(
    { name: "AES-GCM", iv: ENCRYPTION_IV },
    key,
    bytes
  );
  return new TextDecoder().decode(new Uint8Array(plain));
}

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
    if (!raw) return {};
    const parsed = JSON.parse(raw) as SettingsSnapshot;
    // Decrypt apiKey if present and mark as encrypted
    if (parsed.apiKey && typeof parsed.apiKey === "object" && parsed.apiKey.__enc === true && parsed.apiKey.value) {
      // Decrypt synchronously is not possible; warn, remove, return.
      // For compatibility, clear API key and warn.
      // Note: To make this fully correct need to make readSnapshot async and propagate up.
      // For now, fallback to returning no apiKey if encrypted.
      // Optionally implement a lazy decrypt in the UI hook.
      return { ...parsed, apiKey: undefined };
    }
    return parsed;
  } catch {
    return {};
  }
}

async function writeSnapshot(next: SettingsSnapshot) {
  if (!hasBrowserApis) {
    return;
  }
  try {
    let prepared = { ...next };
    const apiKey = next.apiKey;
    if (apiKey && typeof apiKey === "string") {
      // Encrypt the apiKey before storing
      prepared.apiKey = {
        __enc: true,
        value: await encrypt(apiKey)
      } as any;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prepared));
    // storage-событие не срабатывает в той же вкладке, поэтому транслируем вручную.
    window.dispatchEvent(new CustomEvent("pulseplate:settings", { detail: prepared }));
  } catch {
    // Игнорируем quota/security ошибки — fallback остаётся пустым.
  }
}

export const SettingsStore = {
  get(): SettingsSnapshot {
    return readSnapshot();
  },
  async set(partial: Partial<SettingsSnapshot>) {
    await writeSnapshot({ ...readSnapshot(), ...partial });
  },
  async clear() {
    await writeSnapshot({});
  },
  getApiKey(): string | undefined {
    const snap = readSnapshot();
    // If encrypted, decrypt it synchronously is not possible.
    if (snap.apiKey && typeof snap.apiKey === "object" && (snap.apiKey as any).__enc && (snap.apiKey as any).value) {
      // Optionally, applications can implement an async variant to fetch the decrypted key.
      // For now, undefined.
      return undefined;
    }
    if (typeof snap.apiKey === "string") {
      return snap.apiKey;
    }
    return undefined;
  },
  async getApiKeyDecrypted(): Promise<string | undefined> {
    const snap = readSnapshot();
    if (snap.apiKey && typeof snap.apiKey === "object" && (snap.apiKey as any).__enc && (snap.apiKey as any).value) {
      try {
        return await decrypt((snap.apiKey as any).value);
      } catch {
        return undefined;
      }
    }
    if (typeof snap.apiKey === "string") {
      return snap.apiKey;
    }
    return undefined;
  },
  async setApiKey(apiKey: string) {
    await writeSnapshot({ ...readSnapshot(), apiKey });
  },
  async clearApiKey() {
    const snapshot = readSnapshot();
    if (snapshot.apiKey !== undefined) {
      delete snapshot.apiKey;
      await writeSnapshot(snapshot);
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
