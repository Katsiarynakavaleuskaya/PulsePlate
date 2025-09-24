// RU: Простой помощник для вызова API; фронт/Capacitor может подменять baseURL.
// EN: Tiny helper; baseURL can be swapped for Capacitor/native.
const BASE_URL = "/";

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(new URL(path, BASE_URL), {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}
