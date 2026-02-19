import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { trackHppCtaClick, trackHppCtaImpression, trackHppLiveIndicatorImpression } from '../../lib/hppTelemetry';
import { useHppLiveIndicator } from './useHppLiveIndicator';

type HppIndicatorSource = 'home' | 'plate' | 'progress';

interface LiveProgressIndicatorProps {
  source: HppIndicatorSource;
  ctaTo: string;
  ctaLabel: string;
}

export default function LiveProgressIndicator({
  source,
  ctaTo,
  ctaLabel,
}: LiveProgressIndicatorProps) {
  const { status, lastEventAt } = useHppLiveIndicator();
  const trackedImpressionRef = useRef(false);

  useEffect(() => {
    if (trackedImpressionRef.current) {
      return;
    }
    trackedImpressionRef.current = true;
    trackHppLiveIndicatorImpression({ source, live_status: status });
    trackHppCtaImpression({ source, live_status: status, cta_to: ctaTo });
  }, [ctaTo, source, status]);

  const statusLabel = status === 'live' ? 'Live updates on' : 'Static fallback';
  const dotClass = status === 'live' ? 'bg-[var(--color-success)] animate-pulse' : 'bg-[var(--color-warning)]';

  return (
    <section
      className="rounded-xl border p-4 space-y-3"
      style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
      aria-label="Live progress indicator"
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
        className="inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white"
        onClick={() => trackHppCtaClick({ source, live_status: status, cta_to: ctaTo })}
      >
        {ctaLabel}
      </Link>
    </section>
  );
}
