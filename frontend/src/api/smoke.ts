// Не делает сетевых запросов, только предупреждает в консоль.
import { API_BASE } from "./client";
import { log } from "../lib/analytics";

export function apiSmoke(): void {
  const mockEnabled =
    typeof window !== "undefined" && typeof window.location?.search === "string"
      ? new URLSearchParams(window.location.search).get("mock") === "1"
      : false;
  log("api_smoke", { base: API_BASE || "(not set)", mock: mockEnabled });
}
