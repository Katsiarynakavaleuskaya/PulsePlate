// RU: простая заглушка для событий, позже заменим на PostHog/Amplitude.
// EN: tiny stub for events; swap later with PostHog/Amplitude.

type Payload = Record<string, unknown>;

type AnalyticsError = unknown;

/**
 * Logs an analytics event with optional payload data.
 *
 * @param event - The event name to log
 * @param payload - Optional data to include with the event
 */
export function log(event: string, payload: Payload = {}): void {
  console.info(`[analytics] ${event}`, payload);
}

/**
 * Logs an error to analytics with appropriate formatting.
 *
 * @param error - The error to log (Error instance or unknown type)
 */
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
  PURCHASE_FAILURE: "purchase_failure",
  RESTORE_SUCCESS: "restore_success",
} as const;
