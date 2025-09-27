// Не делает сетевых запросов, только предупреждает в консоль.
import { API_BASE } from "./client";

export function apiSmoke(): void {
  const mockEnabled =
    typeof window !== "undefined" && typeof window.location?.search === "string"
      ? new URLSearchParams(window.location.search).get("mock") === "1"
      : false;
  // eslint-disable-next-line no-console
  console.log(`[API] base => ${API_BASE || "(not set)"} | mock=${mockEnabled}`);
}
