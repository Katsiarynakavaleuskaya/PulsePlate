// Не делает сетевых запросов, только предупреждает в консоль.
import { API_BASE } from "./client";

/**
 * Logs the current API base and whether the "mock" query parameter equals "1".
 *
 * The message is written to the console in the format: "[API] base => <API_BASE or (not set)> | mock=<true|false>".
 */
export function apiSmoke(): void {
  const mockEnabled =
    typeof window !== "undefined" && typeof window.location?.search === "string"
      ? new URLSearchParams(window.location.search).get("mock") === "1"
      : false;
  console.log(`[API] base => ${API_BASE || "(not set)"} | mock=${mockEnabled}`);
}