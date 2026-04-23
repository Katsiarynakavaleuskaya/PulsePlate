import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  trackHppCtaClick,
  trackHppCtaImpression,
  trackHppLiveIndicatorImpression,
  trackHppPaywallOpenFromLive,
} from '../../lib/hppTelemetry';
import { type HppLiveVariant, useHppLiveIndicator } from './useHppLiveIndicator';
import { ProgressIndicator, buttonClasses } from '../../components/ui';

type HppIndicatorSource = 'home' | 'plate' | 'progress';

interface LiveProgressIndicatorProps {
  source: HppIndicatorSource;
  ctaTo: string;
  ctaLabel: string;
  variant?: HppLiveVariant;
}

export default function LiveProgressIndicator({
  source,
  ctaTo,
  ctaLabel,
  variant,
}: LiveProgressIndicatorProps) {
  const { status, lastEventAt, variant: assignedVariant } = useHppLiveIndicator();
  const resolvedVariant = variant ?? assignedVariant;
  const lastImpressionKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const impressionKey = `${source}|${ctaTo}|${resolvedVariant}|${status}`;
    if (lastImpressionKeyRef.current === impressionKey) {
      return;
    }
    lastImpressionKeyRef.current = impressionKey;

    const basePayload = {
      source: 'hpp_live_indicator' as const,
      placement: source,
      live_status: status,
      variant: resolvedVariant,
    };
    trackHppLiveIndicatorImpression(basePayload);
    trackHppCtaImpression({ ...basePayload, cta_to: ctaTo });
  }, [ctaTo, resolvedVariant, source, status]);

  const statusLabel = status === 'live' ? 'Live updates on' : 'Static fallback';
  const path = ctaTo.split('?')[0];
  const isPaywallCta = /^\/pro(?:\/|$)/.test(path) || /^\/paywall(?:\/|$)/.test(path);

  return (
    <ProgressIndicator
      action={
        <Link
          to={ctaTo}
          className={buttonClasses({
            className:
              resolvedVariant === 'emphasized'
                ? 'inline-flex rounded-lg px-5 py-2.5'
                : 'inline-flex rounded-lg px-4 py-2',
          })}
          onClick={() => {
            const basePayload = {
              source: 'hpp_live_indicator' as const,
              placement: source,
              live_status: status,
              variant: resolvedVariant,
              cta_to: ctaTo,
            };
            trackHppCtaClick(basePayload);
            if (isPaywallCta) {
              trackHppPaywallOpenFromLive(basePayload);
            }
          }}
        >
          {ctaLabel}
        </Link>
      }
      aria-label="Live progress indicator"
      data-variant={resolvedVariant}
      description="If realtime is unavailable, PulsePlate stays usable and keeps CTA flow active."
      label={statusLabel}
      state={status === 'live' ? 'live' : 'static'}
      timestampAriaLabel="Live event timestamp"
      timestampLabel={lastEventAt ? new Date(lastEventAt).toLocaleTimeString() : undefined}
      variant={resolvedVariant}
    />
  );
}
