import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { getWeeklyPlan, type WeeklyMenuResponse } from '../../api/premium/weekly-plan';
import type { TargetsRequest } from '../../api/premium/types';
import { WeeklyPlanSkeleton } from './WeeklyPlanSkeleton.tsx';
import { WeeklyPlanError } from './WeeklyPlanError.tsx';
import { WeeklyPlanEmpty } from './WeeklyPlanEmpty.tsx';
import { DayMenuCard } from './DayMenuCard';

interface WeeklyPlanReaderProps {
  request?: TargetsRequest;
  onError?: (error: Error) => void;
  className?: string;
  'data-testid'?: string;
}

const DAYS_OF_WEEK = [
  'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
] as const;

export function WeeklyPlanReader({
  request,
  onError,
  className = '',
  'data-testid': dataTestId = 'weekly-plan-root'
}: WeeklyPlanReaderProps) {
  const { t } = useTranslation();
  const [currentDayIndex, setCurrentDayIndex] = useState(0);
  const [data, setData] = useState<WeeklyMenuResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (request) {
      loadWeeklyPlan(request);
    }
  }, [request]);

  const loadWeeklyPlan = async (req: TargetsRequest) => {
    setLoading(true);
    setError(null);

    try {
      const response = await getWeeklyPlan(req);
      setData(response);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to load weekly plan');
      setError(error);
      onError?.(error);
    } finally {
      setLoading(false);
    }
  };

  const handlePreviousDay = () => {
    setCurrentDayIndex(prev => (prev > 0 ? prev - 1 : DAYS_OF_WEEK.length - 1));
  };

  const handleNextDay = () => {
    setCurrentDayIndex(prev => (prev < DAYS_OF_WEEK.length - 1 ? prev + 1 : 0));
  };

  const handleDaySelect = (dayIndex: number) => {
    setCurrentDayIndex(dayIndex);
  };

  // Loading state
  if (loading) {
    return <WeeklyPlanSkeleton className={className} />;
  }

  // Error state
  if (error) {
    return (
      <WeeklyPlanError
        error={error}
        onRetry={() => request && loadWeeklyPlan(request)}
        className={className}
      />
    );
  }

  // Empty state
  if (!data || !data.daily_menus || data.daily_menus.length === 0) {
    return <WeeklyPlanEmpty className={className} />;
  }

  // Ensure currentDayIndex is within bounds
  const safeDayIndex = Math.max(0, Math.min(currentDayIndex, data.daily_menus.length - 1));
  const currentDay = DAYS_OF_WEEK[safeDayIndex];
  const currentDayData = data.daily_menus[safeDayIndex];
  const weekStartDate = data.week_summary?.week_start
    ? new Date(data.week_summary.week_start)
    : null;
  const formattedWeekStart = weekStartDate ? weekStartDate.toLocaleDateString() : '';

  return (
    <div className={`weekly-plan-reader ${className}`} data-testid={dataTestId}>
      {/* Header with week summary */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('weeklyPlan.title', 'Weekly Meal Plan')}
          </h1>
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <Calendar className="w-4 h-4" />
            <span>
              {t('weeklyPlan.weekOf', 'Week of')}
              {formattedWeekStart ? ` ${formattedWeekStart}` : ''}
            </span>
          </div>
        </div>

        {/* Week coverage summary */}
        {data.weekly_coverage && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg">
              <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">
                {t('weeklyPlan.protein', 'Protein')}
              </div>
              <div className="text-lg font-bold text-blue-900 dark:text-blue-100">
                {data.weekly_coverage.protein || 0}%
              </div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
              <div className="text-sm text-green-600 dark:text-green-400 font-medium">
                {t('weeklyPlan.carbs', 'Carbs')}
              </div>
              <div className="text-lg font-bold text-green-900 dark:text-green-100">
                {data.weekly_coverage.carbs || 0}%
              </div>
            </div>
            <div className="bg-yellow-50 dark:bg-yellow-900/20 p-3 rounded-lg">
              <div className="text-sm text-yellow-600 dark:text-yellow-400 font-medium">
                {t('weeklyPlan.fat', 'Fat')}
              </div>
              <div className="text-lg font-bold text-yellow-900 dark:text-yellow-100">
                {data.weekly_coverage.fat || 0}%
              </div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 p-3 rounded-lg">
              <div className="text-sm text-purple-600 dark:text-purple-400 font-medium">
                {t('weeklyPlan.fiber', 'Fiber')}
              </div>
              <div className="text-lg font-bold text-purple-900 dark:text-purple-100">
                {data.weekly_coverage.fiber || 0}%
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Day navigation */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={handlePreviousDay}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handlePreviousDay();
              }
            }}
            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            aria-label={t('weeklyPlan.previousDay', 'Previous day')}
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <h2
            className="text-xl font-semibold text-gray-900 dark:text-white capitalize"
            aria-label={t(`weeklyPlan.days.${currentDay}`, currentDay)}
          >
            {t(`weeklyPlan.days.${currentDay}`, currentDay)}
          </h2>

          <button
            onClick={handleNextDay}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleNextDay();
              }
            }}
            className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            aria-label={t('weeklyPlan.nextDay', 'Next day')}
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {/* Day selector */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {DAYS_OF_WEEK.map((day, index) => (
            <button
              key={day}
              onClick={() => handleDaySelect(index)}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                index === safeDayIndex
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
              }`}
              aria-label={t(`weeklyPlan.days.${day}`, day)}
              aria-current={index === safeDayIndex ? 'true' : undefined}
            >
              {t(`weeklyPlan.days.${day}`, day)}
            </button>
          ))}
        </div>
      </div>

      {/* Current day menu */}
      <DayMenuCard day={currentDay} dayData={currentDayData} dayIndex={safeDayIndex} />

      {/* Shopping list summary */}
      {data.shopping_list && Object.keys(data.shopping_list).length > 0 && (
        <div className="mt-8 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            {t('weeklyPlan.shoppingList', 'Shopping List')}
          </h3>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {t('weeklyPlan.shoppingListItems', '{{count}} items', {
              count: Object.keys(data.shopping_list).length
            })}
          </div>
        </div>
      )}
    </div>
  );
}
