// RU: Простой помощник для вызова API; фронт/Capacitor может подменять baseURL.
// EN: Tiny helper; baseURL can be swapped for Capacitor/native.
const BASE_URL = "";

function resolveUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  if (BASE_URL) {
    const base = BASE_URL.endsWith("/") ? BASE_URL.slice(0, -1) : BASE_URL;
    const cleanPath = path.startsWith("/") ? path.slice(1) : path;
    return `${base}/${cleanPath}`;
  }
  return path;
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(resolveUrl(path), {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}
