// Не делает сетевых запросов, только предупреждает в консоль.
import { API_BASE } from "./client";

/**
 * Logs the API base and whether mock mode is enabled to the console for diagnostics.
 *
 * The message is formatted as: "[API] base => <API_BASE or '(not set)'> | mock=<true|false>".
 */
export function apiSmoke(): void {
  const mockEnabled =
    typeof window !== "undefined" && typeof window.location?.search === "string"
      ? new URLSearchParams(window.location.search).get("mock") === "1"
      : false;
  console.log(`[API] base => ${API_BASE || "(not set)"} | mock=${mockEnabled}`);
}