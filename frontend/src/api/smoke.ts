// Не делает сетевых запросов, только предупреждает в консоль.
import { API_BASE } from "./client";

/**
 * Logs the configured API base and whether mock mode is enabled.
 *
 * The console message includes the value of `API_BASE` (or "(not set)" if falsy) and a `mock` flag derived from the URL search parameter `mock=1` when running in a browser.
 */
export function apiSmoke(): void {
  const mockEnabled =
    typeof window !== "undefined" && typeof window.location?.search === "string"
      ? new URLSearchParams(window.location.search).get("mock") === "1"
      : false;
  console.log(`[API] base => ${API_BASE || "(not set)"} | mock=${mockEnabled}`);
}
