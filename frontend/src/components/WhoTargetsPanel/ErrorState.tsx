import { useTranslation } from 'react-i18next';
import { clsx } from 'clsx';

interface ErrorStateProps {
  error: string;
  onRetry?: () => void;
  className?: string;
}

export function WhoTargetsErrorState({ error, onRetry, className }: ErrorStateProps) {
  const { t } = useTranslation();

  return (
    <div className={clsx('who-targets-panel__error', className)}>
      <div className="error-state">
        <div className="error-state__icon" aria-hidden="true">
          ⚠️
        </div>
        <h3 className="error-state__title">
          {t('whoTargets.error.title', 'Unable to Calculate Targets')}
        </h3>
        <p className="error-state__message">
          {error}
        </p>
        <button
          type="button"
          className="btn btn--primary btn-touch"
          onClick={onRetry || (() => window.location.reload())}
        >
          {t('whoTargets.error.retry', 'Try Again')}
        </button>
      </div>
    </div>
  );
}
