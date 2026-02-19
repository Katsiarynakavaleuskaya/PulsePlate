import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  HPP_EVENTS,
  trackHppCtaClick,
  trackHppCtaImpression,
  trackHppLiveIndicatorImpression,
  trackHppPaywallOpenFromLive,
} from '../../../lib/hppTelemetry';

const mockLog = vi.fn();

vi.mock('../../../lib/analytics', () => ({
  log: (...args: unknown[]) => mockLog(...args),
}));

describe('hppTelemetry', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('logs impression and cta events with stable payload shape', () => {
    const payload = {
      source: 'hpp_live_indicator' as const,
      placement: 'home' as const,
      live_status: 'static' as const,
      variant: 'compact' as const,
      cta_to: '/progress',
    };

    trackHppLiveIndicatorImpression({
      source: payload.source,
      placement: payload.placement,
      live_status: payload.live_status,
      variant: payload.variant,
    });
    trackHppCtaImpression(payload);
    trackHppCtaClick(payload);
    trackHppPaywallOpenFromLive(payload);

    expect(mockLog).toHaveBeenNthCalledWith(1, HPP_EVENTS.LIVE_INDICATOR_IMPRESSION, {
      source: 'hpp_live_indicator',
      placement: 'home',
      live_status: 'static',
      variant: 'compact',
    });
    expect(mockLog).toHaveBeenNthCalledWith(2, HPP_EVENTS.CTA_IMPRESSION, payload);
    expect(mockLog).toHaveBeenNthCalledWith(3, HPP_EVENTS.CTA_CLICK, payload);
    expect(mockLog).toHaveBeenNthCalledWith(4, HPP_EVENTS.PAYWALL_OPEN_FROM_LIVE, payload);
  });
});
