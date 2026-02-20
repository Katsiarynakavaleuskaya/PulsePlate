import { Link } from 'react-router-dom';
import { getStoredApiKey } from '../auth/storage';
import { pageCardStyle } from '../components/ui/pageCardStyle';

export default function Profile() {
  const hasApiKey = getStoredApiKey() !== null;

  return (
    <main className="flex min-h-screen flex-col bg-[var(--color-bg)]">
      {/* Header Section */}
      <section className="px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
            Settings & Configuration
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-[var(--color-text)] sm:text-5xl">
            Profile
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-[var(--color-text-muted)]">
            Manage your wellness configuration, API connection, and nutrition profile settings.
            Keep your preferences and data synchronized across devices.
          </p>
        </div>
      </section>

      {/* Configuration Status */}
      <section className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div
            style={pageCardStyle}
            className="overflow-hidden p-6 transition-shadow hover:shadow-md"
          >
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              Configuration Status
            </h2>

            {/* Status Item */}
            <div className="mt-6 space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-[var(--color-text)]">
                    API Connection
                  </p>
                  <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                    Required for personalized guidance
                  </p>
                </div>
                <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                  hasApiKey
                    ? 'bg-[var(--color-success)] text-white'
                    : 'bg-[var(--color-error)] text-white'
                }`}>
                  {hasApiKey ? 'Connected' : 'Missing'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Actions Section */}
      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-[var(--color-text)]">
              Configuration
            </h2>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Update your API key and nutrition profile
            </p>
          </div>

          {/* Primary Action */}
          <div className="mb-4">
            <Link
              to="/enter-key"
              className="block w-full rounded-xl bg-[var(--color-primary)] px-6 py-4 text-center font-semibold text-[var(--color-primary-foreground)] transition-all hover:shadow-md hover:opacity-95 active:scale-95"
            >
              {hasApiKey ? 'Update API Key' : 'Configure API Key'}
            </Link>
          </div>

          {/* Secondary Action */}
          <div>
            <Link
              to="/setup"
              className="block w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-6 py-4 text-center font-semibold text-[var(--color-text)] transition-all hover:bg-[var(--color-surface)] hover:shadow-sm active:scale-95"
            >
              Configure Nutrition Profile
            </Link>
          </div>

          {/* Info Card */}
          <section className="mt-8 overflow-hidden rounded-xl" style={pageCardStyle}>
            <div className="p-6">
              <h3 className="text-base font-semibold text-[var(--color-text)]">
                About PulsePlate
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[var(--color-text-muted)]">
                PulsePlate is your personal wellness companion. We help you track nutrition, optimize your health
                metrics, and achieve sustainable wellness goals through personalized guidance powered by advanced
                analytics.
              </p>
              <p className="mt-4 text-xs text-[var(--color-text-muted)]">
                Version 1.0 • Made with care for your wellness journey
              </p>
            </div>
          </section>
        </div>
      </section>

      {/* Footer Spacing */}
      <div className="h-24" />
    </main>
  );
}
