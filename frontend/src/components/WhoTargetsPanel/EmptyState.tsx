import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';
import { ChartBar } from 'lucide-react';

interface EmptyStateProps {
  className?: string;
}

export function WhoTargetsEmptyState({ className }: EmptyStateProps) {
  const { t } = useTranslation();

  return (
    <div className={clsx('who-targets-panel__empty', className)}>
      <div className="empty-state">
        <div className="empty-state__icon">
          <ChartBar
            size={48}
            className="empty-state__icon-svg"
            aria-label={t('whoTargets.empty.iconLabel', 'Nutrition targets chart')}
            role="img"
          />
        </div>
        <h3 className="empty-state__title">
          {t('whoTargets.empty.title', 'No Targets Available')}
        </h3>
        <p className="empty-state__message">
          {t('whoTargets.empty.message', 'Please complete your profile to see personalized nutrition targets.')}
        </p>
      </div>
    </div>
  );
}
