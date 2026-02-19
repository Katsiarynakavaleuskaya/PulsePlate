import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { getStoredApiKey } from '../auth/storage';
import { usePremium } from '../lib/usePremium';

const cardStyle: CSSProperties = {
  backgroundColor: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--pp-radius-xl)',
};

const quickActions = [
  { to: '/setup', label: 'Open setup', primary: true },
  { to: '/plate', label: 'Open plate', primary: false },
  { to: '/progress', label: 'Open progress', primary: false },
  { to: '/pro', label: 'Open Pro', primary: false },
] as const;

export default function Home() {
  const isPremium = usePremium();
  const hasApiKey = getStoredApiKey() !== null;
  const premiumLabel = isPremium === undefined ? 'Checking…' : isPremium ? 'Active' : 'Inactive';
  const statusTone = isPremium === true ? 'text-[var(--color-success)]' : 'text-text';

  return (
    <main className="p-4 pb-24 space-y-4">
      <section className="p-6" style={cardStyle}>
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
        <article className="p-4" style={cardStyle}>
          <p className="text-xs uppercase tracking-wide text-muted">API key</p>
          <p className="mt-2 text-lg font-semibold text-text">{hasApiKey ? 'Connected' : 'Not configured'}</p>
          <p className="mt-2 text-sm text-muted">Setup unlocks personalized guidance and sync.</p>
        </article>

        <article className="p-4" style={cardStyle}>
          <p className="text-xs uppercase tracking-wide text-muted">Premium</p>
          <p className="mt-2 text-lg font-semibold text-text">{premiumLabel}</p>
          <p className="mt-2 text-sm text-muted">Pro enables advanced insights and premium planning views.</p>
        </article>
      </section>

      <section className="p-4 space-y-3" style={cardStyle}>
        <h2 className="text-base font-semibold text-text">Quick actions</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {quickActions.map((action) => (
            <Link
              key={action.to}
              className={`rounded-full px-4 py-3 text-center text-sm font-semibold ${
                action.primary
                  ? 'bg-primary text-white'
                  : 'bg-[var(--color-surface-muted)] text-text'
              }`}
              to={action.to}
            >
              {action.label}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
