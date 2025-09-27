// RU: простая заглушка для событий, позже заменим на PostHog/Amplitude.
// EN: tiny stub for events; swap later with PostHog/Amplitude.
type Payload = Record<string, unknown>;

export function log(event: string, payload: Payload = {}): void {
  // eslint-disable-next-line no-console
  console.info(`[analytics] ${event}`, payload);
}

// Часто используемые имена — чтобы не ошибаться в орфографии.
export const Events = {
  PAYWALL_VIEW: "paywall_view",
  PURCHASE_ATTEMPT: "purchase_attempt",
  PURCHASE_CANCEL: "purchase_cancel",
  PURCHASE_SUCCESS: "purchase_success",
  RESTORE_SUCCESS: "restore_success",
} as const;
