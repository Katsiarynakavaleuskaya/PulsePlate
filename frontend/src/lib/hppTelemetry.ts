import { log } from './analytics';
import type { HppLiveVariant } from '../features/progress/useHppLiveIndicator';

type HppSource = 'home' | 'plate' | 'progress';
type HppLiveStatus = 'live' | 'static';

interface HppBasePayload extends Record<string, unknown> {
  source: 'hpp_live_indicator';
  placement: HppSource;
  live_status: HppLiveStatus;
  variant: HppLiveVariant;
}

interface HppCtaPayload extends HppBasePayload {
  cta_to: string;
}

export const HPP_EVENTS = {
  LIVE_INDICATOR_IMPRESSION: 'hpp_live_indicator_impression',
  CTA_IMPRESSION: 'hpp_cta_impression',
  CTA_CLICK: 'hpp_cta_click',
  PAYWALL_OPEN_FROM_LIVE: 'hpp_paywall_open_from_live',
} as const;

export function trackHppLiveIndicatorImpression(payload: HppBasePayload): void {
  log(HPP_EVENTS.LIVE_INDICATOR_IMPRESSION, payload);
}

export function trackHppCtaImpression(payload: HppCtaPayload): void {
  log(HPP_EVENTS.CTA_IMPRESSION, payload);
}

export function trackHppCtaClick(payload: HppCtaPayload): void {
  log(HPP_EVENTS.CTA_CLICK, payload);
}

export function trackHppPaywallOpenFromLive(payload: HppCtaPayload): void {
  log(HPP_EVENTS.PAYWALL_OPEN_FROM_LIVE, payload);
}
