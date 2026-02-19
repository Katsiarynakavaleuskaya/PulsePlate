import { Link } from 'react-router-dom';
import PremiumGate from "../components/PremiumGate";
import { pageCardStyle } from "../components/ui/pageCardStyle";
import LiveProgressIndicator from '../features/progress/LiveProgressIndicator';
import { usePremium } from "../lib/usePremium";
import { PREMIUM_GATE_SOURCES } from "../config/constants";

export default function Plate() {
  const isPremium = usePremium();

  if (isPremium === undefined) {
    return (
      <main className="p-4 pb-24">
        <section className="p-5" style={pageCardStyle}>
          <h1 className="text-2xl font-bold text-text">Plate</h1>
          <p className="mt-2 text-sm text-muted">Loading…</p>
        </section>
      </main>
    );
  }

  return (
    <main className="p-4 pb-24 space-y-4">
      <section className="p-5" style={pageCardStyle}>
        <h1 className="text-2xl font-bold text-text">Plate</h1>
        <p className="mt-2 text-sm text-muted">
          PRO nutrition slice built on canonical routes and thin-client adapters.
        </p>
      </section>

      <PremiumGate isPremium={isPremium} source={PREMIUM_GATE_SOURCES.PLATE_PAGE}>
        <section className="p-4 space-y-3" style={pageCardStyle}>
          <h2 className="text-base font-semibold text-text">PRO nutrition controls</h2>
          <p className="text-sm text-muted">
            Use setup to refresh targets, then open progress for trend tracking.
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Link className="rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white" to="/setup">
              Open setup
            </Link>
            <Link className="rounded-lg bg-[var(--color-surface-muted)] px-4 py-3 text-sm font-semibold text-text" to="/progress">
              Open progress
            </Link>
          </div>
        </section>
        <LiveProgressIndicator source="plate" ctaTo="/progress" ctaLabel="Open progress live" />
      </PremiumGate>
    </main>
  );
}
