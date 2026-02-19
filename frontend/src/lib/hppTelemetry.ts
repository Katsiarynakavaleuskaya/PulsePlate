import { log } from './analytics';

type HppSource = 'home' | 'plate' | 'progress';
type HppLiveStatus = 'live' | 'static';

interface HppBasePayload extends Record<string, unknown> {
  source: HppSource;
  live_status: HppLiveStatus;
}

interface HppCtaPayload extends HppBasePayload {
  cta_to: string;
}

export const HPP_EVENTS = {
  LIVE_INDICATOR_IMPRESSION: 'hpp_live_indicator_impression',
  CTA_IMPRESSION: 'hpp_cta_impression',
  CTA_CLICK: 'hpp_cta_click',
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
