import type { JSX } from 'react';
import ProgressCharts from '../features/progress/ProgressCharts';
import { useState } from 'react';
import SegmentedControl from '../components/ui/SegmentedControl';

type ProgressWindow = '7D' | '30D' | '90D';

export default function Progress(): JSX.Element {
  const [windowRange, setWindowRange] = useState<ProgressWindow>('30D');

  return (
    <main className="p-4 pb-24 space-y-4" style={{ backgroundColor: 'var(--pp-navy)', minHeight: '100vh' }}>
      <section
        className="rounded-2xl border p-4"
        style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text">Progress</h1>
            <p className="mt-2 text-sm text-muted">Daily and weekly trend surface for Home+Plate slice.</p>
          </div>
          <SegmentedControl
            options={['7D', '30D', '90D'] as const}
            value={windowRange}
            onChange={setWindowRange}
            ariaLabel="Progress date range"
          />
        </div>
      </section>
      <ProgressCharts windowRange={windowRange} />
    </main>
  );
}
