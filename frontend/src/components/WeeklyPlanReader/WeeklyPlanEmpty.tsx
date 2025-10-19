import { Calendar, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface WeeklyPlanEmptyProps {
  className?: string;
  onGeneratePlan?: () => void;
}

export function WeeklyPlanEmpty({ className = '', onGeneratePlan }: WeeklyPlanEmptyProps) {
  const { t } = useTranslation();

  return (
    <div className={`weekly-plan-empty ${className}`} data-testid="weekly-plan-empty">
      <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
        <div className="mb-6">
          <Calendar className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {t('weeklyPlan.empty.title', 'No weekly plan available')}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4 max-w-md">
            {t(
              'weeklyPlan.empty.message',
              'Generate your personalized weekly meal plan to get started with your nutrition journey.'
            )}
          </p>
        </div>

        <button
          onClick={onGeneratePlan}
          disabled={!onGeneratePlan}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-blue-600"
        >
          <Plus className="w-4 h-4" />
          {t('weeklyPlan.empty.generate', 'Generate Weekly Plan')}
        </button>

        <div className="mt-6 text-sm text-gray-500 dark:text-gray-400">
          <p>
            {t(
              'weeklyPlan.empty.help',
              'Complete your profile setup to generate a personalized meal plan.'
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
