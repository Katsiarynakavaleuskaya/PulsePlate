import { Clock, Utensils } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface MealItem {
  name: string;
  calories?: number;
  protein?: number;
  carbs?: number;
  fat?: number;
  fiber?: number;
  serving_size?: string;
  ingredients?: string[];
}

interface DayMenuData {
  meals?: {
    breakfast?: MealItem[];
    lunch?: MealItem[];
    dinner?: MealItem[];
    snacks?: MealItem[];
  };
  total_calories?: number;
  total_protein?: number;
  total_carbs?: number;
  total_fat?: number;
  total_fiber?: number;
}

interface DayMenuCardProps {
  day: string;
  dayData?: DayMenuData;
  dayIndex: number;
}

const MEAL_ORDER = ['breakfast', 'lunch', 'dinner', 'snacks'] as const;

export function DayMenuCard({ dayData }: DayMenuCardProps) {
  const { t } = useTranslation();

  if (!dayData || !dayData.meals) {
    return (
      <div className="p-6 border border-gray-200 dark:border-gray-700 rounded-lg">
        <div className="text-center text-gray-500 dark:text-gray-400">
          <Utensils className="w-8 h-8 mx-auto mb-2" />
          <p>{t('weeklyPlan.noMeals', 'No meals planned for this day')}</p>
        </div>
      </div>
    );
  }

  const meals = dayData.meals;
  const totalCalories = dayData.total_calories || 0;

  return (
    <div className="day-menu-card">
      {/* Day summary */}
      <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <span className="font-medium text-blue-900 dark:text-blue-100">
              {t('weeklyPlan.totalCalories', 'Total Calories')}
            </span>
          </div>
          <span className="text-xl font-bold text-blue-900 dark:text-blue-100">
            {totalCalories.toLocaleString()}
          </span>
        </div>

        {/* Macronutrient breakdown */}
        {(dayData.total_protein || dayData.total_carbs || dayData.total_fat) && (
          <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
            {dayData.total_protein && (
              <div className="text-center">
                <div className="text-gray-600 dark:text-gray-400">Protein</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {dayData.total_protein}g
                </div>
              </div>
            )}
            {dayData.total_carbs && (
              <div className="text-center">
                <div className="text-gray-600 dark:text-gray-400">Carbs</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {dayData.total_carbs}g
                </div>
              </div>
            )}
            {dayData.total_fat && (
              <div className="text-center">
                <div className="text-gray-600 dark:text-gray-400">Fat</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {dayData.total_fat}g
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Meals */}
      <div className="space-y-4">
        {MEAL_ORDER.map((mealType) => {
          const mealItems = meals[mealType];
          if (!mealItems || mealItems.length === 0) return null;

          const mealCalories = mealItems.reduce((sum, item) => sum + (item.calories || 0), 0);

          return (
            <div key={mealType} className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                  {t(`weeklyPlan.meals.${mealType}`, mealType)}
                </h3>
                <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
                  <Clock className="w-4 h-4" />
                  <span>{mealCalories} cal</span>
                </div>
              </div>

              <div className="space-y-3">
                {mealItems.map((item, index) => (
                  <div key={index} className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {item.name}
                      </h4>
                      {item.serving_size && (
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {item.serving_size}
                        </p>
                      )}
                      {item.ingredients && item.ingredients.length > 0 && (
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                          {item.ingredients.join(', ')}
                        </p>
                      )}
                    </div>
                    <div className="text-right text-sm">
                      {item.calories && (
                        <div className="font-medium text-gray-900 dark:text-white">
                          {item.calories} cal
                        </div>
                      )}
                      {(item.protein || item.carbs || item.fat) && (
                        <div className="text-gray-600 dark:text-gray-400">
                          {item.protein && `${item.protein}p`}
                          {item.protein && (item.carbs || item.fat) && ' • '}
                          {item.carbs && `${item.carbs}c`}
                          {item.carbs && item.fat && ' • '}
                          {item.fat && `${item.fat}f`}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* No meals message */}
      {Object.keys(meals).length === 0 && (
        <div className="p-6 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <Utensils className="w-8 h-8 mx-auto mb-2" />
            <p>{t('weeklyPlan.noMeals', 'No meals planned for this day')}</p>
          </div>
        </div>
      )}
    </div>
  );
}
