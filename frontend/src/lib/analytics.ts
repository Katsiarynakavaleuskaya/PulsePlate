// RU: простая заглушка для событий, позже заменим на PostHog/Amplitude.
// EN: tiny stub for events; swap later with PostHog/Amplitude.
type Payload = Record<string, unknown>;

type AnalyticsError = unknown;

export function log(event: string, payload: Payload = {}): void {
  console.info(`[analytics] ${event}`, payload);
}

export function logError(error: AnalyticsError): void {
  if (error instanceof Error) {
    console.warn("[analytics] error", error.message);
    return;
  }
  console.warn("[analytics] unknown error", error);
}
// Часто используемые имена — чтобы не ошибаться в орфографии.
export const Events = {
  PAYWALL_VIEW: "paywall_view",
  PURCHASE_ATTEMPT: "purchase_attempt",
  PURCHASE_CANCEL: "purchase_cancel",
  PURCHASE_SUCCESS: "purchase_success",
  RESTORE_SUCCESS: "restore_success",
} as const;
