// Не делает сетевых запросов, только предупреждает в консоль.
import { API_BASE } from "./client";

export function apiSmoke(): void {
  // eslint-disable-next-line no-console
  console.log(`[API] base => ${API_BASE || "(not set)"}`);
}
