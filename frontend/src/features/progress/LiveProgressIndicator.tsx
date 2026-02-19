import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  trackHppCtaClick,
  trackHppCtaImpression,
  trackHppLiveIndicatorImpression,
  trackHppPaywallOpenFromLive,
} from '../../lib/hppTelemetry';
import { type HppLiveVariant, useHppLiveIndicator } from './useHppLiveIndicator';

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

  useEffect(() => {
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
  const dotClass = status === 'live' ? 'bg-[var(--color-success)] animate-pulse' : 'bg-[var(--color-warning)]';
  const containerClass =
    resolvedVariant === 'emphasized' ? 'rounded-xl border p-5 space-y-3 shadow-sm' : 'rounded-xl border p-4 space-y-3';
  const ctaClass =
    resolvedVariant === 'emphasized'
      ? 'inline-flex rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-white'
      : 'inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white';
  const isPaywallCta = ctaTo.includes('/pro') || ctaTo.includes('/paywall');

  return (
    <section
      className={containerClass}
      style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
      aria-label="Live progress indicator"
      data-variant={resolvedVariant}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${dotClass}`} aria-hidden="true" />
          <p className="text-sm font-medium text-text">{statusLabel}</p>
        </div>
        {lastEventAt ? (
          <p className="text-xs text-muted" aria-label="Live event timestamp">
            {new Date(lastEventAt).toLocaleTimeString()}
          </p>
        ) : null}
      </div>
      <p className="text-xs text-muted">
        If realtime is unavailable, PulsePlate stays usable and keeps CTA flow active.
      </p>
      <Link
        to={ctaTo}
        className={ctaClass}
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
    </section>
  );
}
