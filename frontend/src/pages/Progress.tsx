import ProgressCharts from '../features/progress/ProgressCharts';
import LiveProgressIndicator from '../features/progress/LiveProgressIndicator';
import { useState } from 'react';
import SegmentedControl from '../components/ui/SegmentedControl';
import { Card, CardContent } from '../components/ui';

type ProgressWindow = 'WEEK' | 'MONTH' | 'QUARTER';

export default function Progress(): JSX.Element {
  const [windowRange, setWindowRange] = useState<ProgressWindow>('MONTH');

  const dateRangeLabel = {
    WEEK: 'Last week',
    MONTH: 'Last month',
    QUARTER: 'Last quarter',
  }[windowRange];

  return (
    <main className="flex min-h-screen flex-col bg-[var(--color-bg)]">
      {/* Header Section */}
      <section className="px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
            Your wellness journey
          </p>
          <div className="mt-4 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-[var(--color-text)] sm:text-5xl">
                Progress
              </h1>
              <p className="mt-3 text-lg text-[var(--color-text-muted)]">
                Track your daily trends and long-term health outcomes
              </p>
            </div>
            <div className="flex-shrink-0">
              <SegmentedControl
                options={['WEEK', 'MONTH', 'QUARTER'] as const}
                value={windowRange}
                onChange={setWindowRange}
                ariaLabel="Progress time range filter"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Sub-header with Date Range */}
      <section className="border-b border-[var(--color-border)] px-4 py-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <p className="text-sm font-medium text-[var(--color-text-muted)]">
            Viewing: {dateRangeLabel}
          </p>
        </div>
      </section>

      {/* Main Content */}
      <section className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Live Progress Indicator */}
          <Card>
            <CardContent className="p-4">
              <LiveProgressIndicator source="progress" ctaTo="/setup" ctaLabel="Update setup parameters" />
            </CardContent>
          </Card>

          {/* Charts Section */}
          <Card>
            <CardContent className="space-y-4 p-4">
            <ProgressCharts windowRange={windowRange} />
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer Spacing */}
      <div className="h-24" />
    </main>
  );
}
