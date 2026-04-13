// RU: простая заглушка для событий, позже заменим на PostHog/Amplitude.
// EN: tiny stub for events; swap later with PostHog/Amplitude.

type Payload = Record<string, unknown>;

type AnalyticsError = unknown;

export type PaywallExposureEventName =
  | "shown"
  | "dismissed"
  | "cta_clicked"
  | "upgrade_started"
  | "upgrade_completed";

export type PaywallExposurePayload = {
  client_event_id: string;
  exposure_id: string;
  event_name: PaywallExposureEventName;
  source_surface: string;
  trigger_reason: string;
  via?: string;
  metadata?: Record<string, unknown>;
};

const legacyPaywallEventMap: Partial<Record<string, PaywallExposureEventName>> = {
  paywall_view: "shown",
  purchase_cancel: "dismissed",
  purchase_attempt: "cta_clicked",
};

function createRandomId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `evt_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function createAnalyticsEventId(): string {
  return createRandomId();
}

export function mapLegacyPaywallEvent(
  event: string
): PaywallExposureEventName | null {
  return legacyPaywallEventMap[event] ?? null;
}

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

export function logPaywallExposure(payload: PaywallExposurePayload): void {
  log(`paywall_exposure.${payload.event_name}`, payload);

  // RU: Analytics never blocks paywall UX; transport errors are fail-open.
  // EN: Analytics must never block paywall UX; transport errors are fail-open.
  void import("../api/client")
    .then(({ postPaywallExposureEvent }) => postPaywallExposureEvent(payload))
    .catch(logError);
}

export function logLegacyPaywallExposure(
  event: string,
  payload: Omit<PaywallExposurePayload, "event_name">
): void {
  const eventName = mapLegacyPaywallEvent(event);
  if (!eventName) {
    return;
  }
  logPaywallExposure({
    ...payload,
    event_name: eventName,
  });
}
