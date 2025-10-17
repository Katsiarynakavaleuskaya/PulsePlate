import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';

interface EmptyStateProps {
  className?: string;
}

export function WhoTargetsEmptyState({ className }: EmptyStateProps) {
  const { t } = useTranslation();

  return (
    <div className={clsx('who-targets-panel__empty', className)}>
      <div className="empty-state">
        <div className="empty-state__icon" aria-hidden="true">
          📊
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
