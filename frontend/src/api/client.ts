// RU: Минимальный клиент для FastAPI. Без моков и MSW на этом шаге.
// EN: Minimal FastAPI client. No mocks/MSW in this step.

export const API_BASE = (import.meta.env.VITE_API_BASE || "") as string;

if (!API_BASE) {
  // Подсказываем в консоль, если забыли .env
  // eslint-disable-next-line no-console
  console.warn("[API] VITE_API_BASE is not set. Create frontend/.env from .env.example");
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "Accept-Language": navigator.language || "en",
    },
    ...init,
  });
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API ${path} failed: HTTP ${res.status}\nResponse body: ${errorBody}`);
  }
  return res.json() as Promise<T>;
}

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
