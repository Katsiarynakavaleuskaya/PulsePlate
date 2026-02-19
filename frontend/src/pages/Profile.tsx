import { Link } from 'react-router-dom';
import { getStoredApiKey } from '../auth/storage';
import { pageCardStyle } from '../components/ui/pageCardStyle';

export default function Profile() {
  const hasApiKey = getStoredApiKey() !== null;

  return (
    <main className="p-4 pb-24 space-y-4">
      <section className="p-5" style={pageCardStyle}>
        <h1 className="text-2xl font-bold text-text">Profile</h1>
        <p className="mt-2 text-sm text-muted">
          Manage key setup, nutrition profile flow, and legal/app entry points.
        </p>
      </section>

      <section className="p-4 space-y-2" style={pageCardStyle}>
        <h2 className="text-base font-semibold text-text">Environment status</h2>
        <p className="text-sm text-muted">API key: {hasApiKey ? 'Configured' : 'Missing'}</p>
      </section>

      <section className="p-4 space-y-3" style={pageCardStyle}>
        <h2 className="text-base font-semibold text-text">Actions</h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Link className="rounded-lg bg-primary px-4 py-3 text-center text-sm font-semibold text-white transition-opacity hover:opacity-90" to="/enter-key">
            Configure API key
          </Link>
          <Link className="rounded-lg bg-[var(--color-surface-muted)] px-4 py-3 text-center text-sm font-semibold text-text transition-colors hover:bg-[var(--color-border)]" to="/setup">
            Open nutrition setup
          </Link>
        </div>
      </section>
    </main>
  );
}
