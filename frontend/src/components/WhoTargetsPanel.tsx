import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';
import type { TargetsApiResponse } from '../api/premium/types';
import './WhoTargetsPanel.css';
import { WhoTargetsSkeleton } from './WhoTargetsPanel/Skeleton';
import { WhoTargetsErrorState } from './WhoTargetsPanel/ErrorState';
import { WhoTargetsEmptyState } from './WhoTargetsPanel/EmptyState';
import { WhoTargetsCards } from './WhoTargetsPanel/TargetCard';

interface WhoTargetsPanelProps {
  data: TargetsApiResponse | null;
  loading: boolean;
  error: string | null;
  onSaveAndContinue: () => void;
  onRetry?: () => void;
  className?: string;
}

export function WhoTargetsPanel({
  data,
  loading,
  error,
  onSaveAndContinue,
  onRetry,
  className,
}: WhoTargetsPanelProps) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div
        className={clsx('who-targets-panel', 'who-targets-panel--loading', className)}
        data-testid="who-targets-panel"
        aria-busy="true"
        aria-live="polite"
      >
        <div className="who-targets-panel__header">
          <h2 className="who-targets-panel__title">
            {t('whoTargets.title', 'WHO Nutrition Targets')}
          </h2>
        </div>
        <div className="who-targets-panel__content">
          <WhoTargetsSkeleton />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={clsx('who-targets-panel', 'who-targets-panel--error', className)}
        data-testid="who-targets-panel"
      >
        <div className="who-targets-panel__header">
          <h2 className="who-targets-panel__title">
            {t('whoTargets.title', 'WHO Nutrition Targets')}
          </h2>
        </div>
        <div className="who-targets-panel__content">
          <WhoTargetsErrorState error={error} onRetry={onRetry} />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div
        className={clsx('who-targets-panel', 'who-targets-panel--empty', className)}
        data-testid="who-targets-panel"
      >
        <div className="who-targets-panel__header">
          <h2 className="who-targets-panel__title">
            {t('whoTargets.title', 'WHO Nutrition Targets')}
          </h2>
        </div>
        <div className="who-targets-panel__content">
          <WhoTargetsEmptyState />
        </div>
      </div>
    );
  }

  return (
    <div
      className={clsx('who-targets-panel', 'who-targets-panel--loaded', className)}
      data-testid="who-targets-panel"
    >
      <div className="who-targets-panel__header">
        <h2 className="who-targets-panel__title">
          {t('whoTargets.title', 'WHO Nutrition Targets')}
        </h2>
        <p className="who-targets-panel__subtitle">
          {t('whoTargets.subtitle', 'Personalized nutrition goals based on WHO guidelines')}
        </p>
      </div>

      <div className="who-targets-panel__content">
        <WhoTargetsCards data={data} />

        {/* CTA Button */}
        <div className="who-targets-panel__actions">
          <button
            type="button"
            className="btn btn--primary btn--large"
            onClick={onSaveAndContinue}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSaveAndContinue();
              }
            }}
          >
            {t('whoTargets.cta.saveAndContinue', 'Save & Get Weekly Plan')}
          </button>
        </div>
      </div>
    </div>
  );
}
