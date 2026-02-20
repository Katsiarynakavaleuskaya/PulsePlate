import { Link } from 'react-router-dom';
import PremiumGate from "../components/PremiumGate";
import { Card, CardContent, buttonClasses } from "../components/ui";
import LiveProgressIndicator from '../features/progress/LiveProgressIndicator';
import { usePremium } from "../lib/usePremium";
import { PREMIUM_GATE_SOURCES } from "../config/constants";

export default function Plate() {
  const isPremium = usePremium();

  if (isPremium === undefined) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--color-bg)]">
        <Card className="mx-auto max-w-md">
          <CardContent className="p-6">
          <h1 className="text-2xl font-bold text-[var(--color-text)]">Plate</h1>
          <p className="mt-3 text-sm text-[var(--color-text-muted)]">Loading your nutrition data…</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-[var(--color-bg)]">
      {/* Header Section */}
      <section className="px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
            Nutrition Tracking
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-[var(--color-text)] sm:text-5xl">
            Your Plate
          </h1>
          <p className="mt-4 text-lg leading-relaxed text-[var(--color-text-muted)]">
            View and manage your daily nutrition targets. Premium features help you optimize your nutrition plan for
            better health outcomes.
          </p>
        </div>
      </section>

      {/* Premium Gate Section */}
      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <PremiumGate isPremium={isPremium} source={PREMIUM_GATE_SOURCES.PLATE_PAGE}>
            {/* Pro Controls */}
            <Card className="mb-6 overflow-hidden">
              <CardContent className="p-6">
                <h2 className="text-xl font-semibold text-[var(--color-text)]">
                  Premium Nutrition Controls
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-muted)]">
                  Configure your nutrition targets through setup, then track your daily progress and long-term trends.
                  Premium features unlock personalized meal optimization and advanced analytics.
                </p>

                <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <Link
                    to="/setup"
                    className={buttonClasses({ variant: 'primary', size: 'md', className: 'block text-center' })}
                  >
                    Configure Setup
                  </Link>
                  <Link
                    to="/progress"
                    className={buttonClasses({ variant: 'secondary', size: 'md', className: 'block text-center' })}
                  >
                    View Progress
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Live Progress Indicator */}
            <LiveProgressIndicator source="plate" ctaTo="/progress" ctaLabel="View detailed progress" />
          </PremiumGate>
        </div>
      </section>

      {/* Footer Spacing */}
      <div className="h-24" />
    </main>
  );
}
