import { Link } from 'react-router-dom';
import { getStoredApiKey } from '../auth/storage';
import { pageCardStyle } from '../components/ui/pageCardStyle';
import { usePremium } from '../lib/usePremium';

export default function Home() {
  const isPremium = usePremium();
  const hasApiKey = getStoredApiKey() !== null;

  return (
    <main className="p-4 pb-24 space-y-4">
      <section className="p-5" style={pageCardStyle}>
        <h1 className="text-2xl font-bold text-text">Home</h1>
        <p className="mt-2 text-sm text-muted">PulsePlate command center for Home, Plate, and Progress.</p>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <article className="p-4" style={pageCardStyle}>
          <p className="text-xs uppercase tracking-wide text-muted">API key</p>
          <p className="mt-2 text-lg font-semibold text-text">{hasApiKey ? 'Connected' : 'Not configured'}</p>
        </article>

        <article className="p-4" style={pageCardStyle}>
          <p className="text-xs uppercase tracking-wide text-muted">Premium</p>
          <p className="mt-2 text-lg font-semibold text-text">
            {isPremium === undefined ? 'Checking…' : isPremium ? 'Active' : 'Inactive'}
          </p>
        </article>
      </section>

      <section className="p-4 space-y-3" style={pageCardStyle}>
        <h2 className="text-base font-semibold text-text">Quick actions</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Link className="rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white" to="/setup">
            Open setup
          </Link>
          <Link className="rounded-lg bg-[var(--color-surface-muted)] px-4 py-3 text-sm font-semibold text-text" to="/plate">
            Open plate
          </Link>
          <Link className="rounded-lg bg-[var(--color-surface-muted)] px-4 py-3 text-sm font-semibold text-text" to="/progress">
            Open progress
          </Link>
          <Link className="rounded-lg bg-[var(--color-surface-muted)] px-4 py-3 text-sm font-semibold text-text" to="/pro">
            Open Pro
          </Link>
        </div>
      </section>
    </main>
  );
}
