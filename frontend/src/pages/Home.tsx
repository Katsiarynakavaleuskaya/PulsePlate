import { Link } from 'react-router-dom';
import { Card, CardContent, buttonClasses } from '../components/ui';
import LiveProgressIndicator from '../features/progress/LiveProgressIndicator';
import { useAuth } from '../lib/auth';
import { usePremium } from '../lib/usePremium';

export default function Home() {
  const isPremium = usePremium();
  const { isAuthenticated, isLoading } = useAuth();
  const hasSession = isAuthenticated;
  const premiumLabel = isPremium === undefined ? 'Checking…' : isPremium ? 'Active' : 'Inactive';
  const statusTone = isPremium === true ? 'text-[var(--color-success)]' : 'text-text';
  const apiStatusLabel = isLoading ? 'Checking…' : hasSession ? 'Connected' : 'Not Set';
  const apiStatusDescription = isLoading
    ? 'Verifying your secure session state with the server.'
    : hasSession
      ? 'Your secure session is active. Personalized guidance is enabled.'
      : 'Configure your API key once to establish a secure session and unlock personalized insights.';

  return (
    <main className="flex min-h-screen flex-col bg-[var(--color-bg)]">
      {/* Hero Section */}
      <section className="px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
            Wellness Control Panel
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-[var(--color-text)] sm:text-5xl">
            Home
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-[var(--color-text-muted)]">
            Quick access to your wellness setup, nutrition tracking, and progress insights. Everything you need for
            optimal health in one place.
          </p>
        </div>
      </section>

      {/* Status Cards */}
      <section className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* API Status Card */}
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex h-full flex-col justify-between p-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
                API Connection
              </p>
              <p className="mt-3 text-2xl font-semibold text-[var(--color-text)]">
                {apiStatusLabel}
              </p>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-muted)]">
              {apiStatusDescription}
            </p>
            </CardContent>
          </Card>

          {/* Premium Status Card */}
          <Card className="transition-shadow hover:shadow-md">
            <CardContent className="flex h-full flex-col justify-between p-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
                Premium Status
              </p>
              <p className={`mt-3 text-2xl font-semibold ${statusTone}`}>
                {premiumLabel}
              </p>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-muted)]">
              {isPremium
                ? 'You have access to advanced analytics and premium nutrition optimization.'
                : 'Upgrade to Pro to unlock advanced insights, meal planning, and premium features.'}
            </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Progress Indicator */}
      <section className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <LiveProgressIndicator source="home" ctaTo="/progress" ctaLabel="View detailed progress" />
        </div>
      </section>

      {/* Quick Actions Section */}
      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-[var(--color-text)]">
              Quick Navigation
            </h2>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              Jump to any section of your wellness journey
            </p>
          </div>

          {/* Primary Action */}
          <div className="mb-4">
            <Link
              to="/setup"
              className={buttonClasses({ variant: 'primary', size: 'lg', fullWidth: true, className: 'block text-center' })}
            >
              Configure Setup
            </Link>
          </div>

          {/* Secondary Actions Grid */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Link
              to="/plate"
              className={buttonClasses({ variant: 'secondary', size: 'md', className: 'block text-center' })}
            >
              Nutrition Plate
            </Link>
            <Link
              to="/progress"
              className={buttonClasses({ variant: 'secondary', size: 'md', className: 'block text-center' })}
            >
              Progress View
            </Link>
            <Link
              to="/pro"
              className={buttonClasses({ variant: 'secondary', size: 'md', className: 'block text-center' })}
            >
              Premium Features
            </Link>
          </div>
        </div>
      </section>

      {/* Footer Spacing for Tab Bar */}
      <div className="h-24" />
    </main>
  );
}
