import type { JSX } from "react";
import { BarChart3 } from "lucide-react";
import { ProgressExportPdfButton } from '../../components/cta';
import { EmptyState } from '../../components/ui';

const chartTokens = {
  primary: 'var(--color-primary)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
  info: 'var(--color-info)',
  text: 'var(--color-text)',
  muted: 'var(--color-text-muted)',
  surface: 'var(--color-surface)',
  border: 'var(--color-border)',
  tooltipBackground: 'var(--color-bg)',
};

type ProgressWindow = 'WEEK' | 'MONTH' | 'QUARTER';

interface ProgressChartsProps {
  windowRange?: ProgressWindow;
}

export default function ProgressCharts({ windowRange = 'MONTH' }: ProgressChartsProps): JSX.Element {
  return (
    <div id="progress-charts" className="space-y-6 p-4">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: chartTokens.text }}>Progress Tracking</h2>
          <p style={{ color: chartTokens.muted }}>Monitor your health journey ({windowRange})</p>
        </div>
        <ProgressExportPdfButton disabled />
      </div>

      <div
        className="rounded-lg p-6 shadow-sm"
        style={{ backgroundColor: chartTokens.surface, border: `1px solid ${chartTokens.border}` }}
      >
        <EmptyState
          icon={BarChart3}
          title="No progress data yet"
          description={`PulsePlate hides charts for ${windowRange.toLowerCase()} views until real nutrition and weight data are available. Connect a live data source, then return here to review trusted trends.`}
        />
      </div>
    </div>
  );
}
