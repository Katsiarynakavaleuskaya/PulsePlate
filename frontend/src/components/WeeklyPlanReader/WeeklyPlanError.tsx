import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface WeeklyPlanErrorProps {
  error: Error;
  onRetry?: () => void;
  className?: string;
}

export function WeeklyPlanError({
  error,
  onRetry,
  className = ''
}: WeeklyPlanErrorProps) {
  const { t } = useTranslation();

  return (
    <div className={`weekly-plan-error ${className}`}>
      <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
        <div className="mb-6">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {t('weeklyPlan.error.title', 'Failed to load weekly plan')}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4 max-w-md">
            {error.message || t('weeklyPlan.error.message', 'Something went wrong while loading your weekly meal plan.')}
          </p>
        </div>

        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            <RefreshCw className="w-4 h-4" />
            {t('weeklyPlan.error.retry', 'Try Again')}
          </button>
        )}

        <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
          <p>{t('weeklyPlan.error.help', 'If the problem persists, please check your internet connection and try again.')}</p>
        </div>
      </div>
    </div>
  );
}
