import { Link } from 'react-router-dom';
import { getStoredApiKey } from '../auth/storage';
import { pageCardStyle } from '../components/ui/pageCardStyle';
import LiveProgressIndicator from '../features/progress/LiveProgressIndicator';
import { usePremium } from '../lib/usePremium';

export default function Home() {
  const isPremium = usePremium();
  const hasApiKey = getStoredApiKey() !== null;
  const premiumLabel = isPremium === undefined ? 'Checking…' : isPremium ? 'Active' : 'Inactive';
  const statusTone = isPremium === true ? 'text-[var(--color-success)]' : 'text-text';

  return (
    <main className="p-4 pb-24 space-y-4">
      <section className="p-6" style={pageCardStyle}>
        <p className="text-xs uppercase tracking-wide text-muted">Today</p>
        <h1 className="mt-2 text-2xl font-bold text-text">Home</h1>
        <p className="mt-2 text-sm text-muted">
          Your wellness control panel with quick access to setup, plate, and progress.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-medium text-text">
            API {hasApiKey ? 'Connected' : 'Missing'}
          </span>
          <span className={`rounded-full bg-[var(--color-surface-muted)] px-3 py-1 text-xs font-medium ${statusTone}`}>
            Premium {premiumLabel}
          </span>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <article className="p-4" style={pageCardStyle}>
          <p className="text-xs uppercase tracking-wide text-muted">API key</p>
          <p className="mt-2 text-lg font-semibold text-text">{hasApiKey ? 'Connected' : 'Not configured'}</p>
          <p className="mt-2 text-sm text-muted">Setup unlocks personalized guidance and sync.</p>
        </article>

        <article className="p-4" style={pageCardStyle}>
          <p className="text-xs uppercase tracking-wide text-muted">Premium</p>
          <p className="mt-2 text-lg font-semibold text-text">{premiumLabel}</p>
          <p className="mt-2 text-sm text-muted">Pro enables advanced insights and premium planning views.</p>
        </article>
      </section>

      <LiveProgressIndicator source="home" ctaTo="/progress" ctaLabel="Open progress live" />

      <section className="p-4 space-y-3" style={pageCardStyle}>
        <h2 className="text-base font-semibold text-text">Quick actions</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Link className="rounded-full bg-primary px-4 py-3 text-center text-sm font-semibold text-white transition-opacity hover:opacity-90" to="/setup">
            Open setup
          </Link>
          <Link className="rounded-full bg-[var(--color-surface-muted)] px-4 py-3 text-center text-sm font-semibold text-text transition-colors hover:bg-[var(--color-border)]" to="/plate">
            Open plate
          </Link>
          <Link className="rounded-full bg-[var(--color-surface-muted)] px-4 py-3 text-center text-sm font-semibold text-text transition-colors hover:bg-[var(--color-border)]" to="/progress">
            Open progress
          </Link>
          <Link className="rounded-full bg-[var(--color-surface-muted)] px-4 py-3 text-center text-sm font-semibold text-text transition-colors hover:bg-[var(--color-border)]" to="/pro">
            Open Pro
          </Link>
        </div>
      </section>
    </main>
  );
}
