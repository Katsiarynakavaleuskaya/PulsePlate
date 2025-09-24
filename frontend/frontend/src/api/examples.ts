// RU: Пример — получить схему (дымо-тест).
// EN: Example — fetch OpenAPI (smoke).
import type { paths } from "./schema";
import { fetchJson } from "./client";

export async function getOpenApi(): Promise<unknown> {
  return fetchJson<unknown>("/openapi.json");
}

export type FoodsSearchResponse =
  paths["/api/v1/foods/search"]["get"]["responses"]["200"]["content"]["application/json"];

export async function searchFoods(q: string): Promise<FoodsSearchResponse> {
  const url = `/api/v1/foods/search?q=${encodeURIComponent(q)}`;
  return fetchJson<FoodsSearchResponse>(url);
}
