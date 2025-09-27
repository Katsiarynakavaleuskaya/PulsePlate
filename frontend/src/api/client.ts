// RU: Минимальный клиент для FastAPI. Без моков и MSW на этом шаге.
// EN: Minimal FastAPI client. No mocks/MSW in this step.

export const API_BASE = (import.meta.env.VITE_API_BASE || "") as string;

if (!API_BASE) {
  // Подсказываем в консоль, если забыли .env
  // eslint-disable-next-line no-console
  console.warn("[API] VITE_API_BASE is not set. Create frontend/.env from .env.example");
}

function mergeHeaders(init?: RequestInit): Headers {
  const defaults = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "Accept-Language": navigator.language || "en",
  } satisfies Record<string, string>;

  const headers = new Headers(defaults);

  if (!init?.headers) {
    return headers;
  }

  const incoming = init.headers instanceof Headers
    ? init.headers
    : new Headers(init.headers as HeadersInit);

  incoming.forEach((value, key) => {
    headers.set(key, value);
  });

  return headers;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: mergeHeaders(init),
  });
  if (!res.ok) {
    const errorBody = await res.text().catch(() => "<response body unavailable>");
    throw new Error(`API ${path} failed: HTTP ${res.status}\nResponse body: ${errorBody}`);
  }
  return res.json() as Promise<T>;
}

export const fetchJson = api;

// Типы минимальные — ровно чтобы начать (уточним позже из OpenAPI)
export type BmrRequest = {
  sex: "male" | "female";
  age: number; // years
  height: number; // cm
  weight: number; // kg
};

export type BmrResponse = {
  bmr: number; // kcal/day
  method: string; // e.g., "Mifflin-St Jeor"
};

export type PlateResponse = {
  calories: number;
  macros: { protein: number; fat: number; carbs: number }; // grams
  micros?: Record<string, number>; // optional micronutrients map
};

export type WeekPlanResponse = {
  days: Array<{ date: string; meals: Array<{ name: string; kcal: number }> }>;
};

// Endpoints
export const getBmr = (body: BmrRequest) =>
  api<BmrResponse>("/premium/bmr", { method: "POST", body: JSON.stringify(body) });

export const getPlate = () => api<PlateResponse>("/premium/plate");

export const getWeekPlan = () => api<WeekPlanResponse>("/plan/week");
