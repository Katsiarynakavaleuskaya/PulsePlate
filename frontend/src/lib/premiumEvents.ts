export const PREMIUM_CHANGE_EVENT = "pp-premium-change";

export function dispatchPremiumChangeEvent(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new Event(PREMIUM_CHANGE_EVENT));
}
