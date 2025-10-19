import { Clock, Utensils } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface MealItem {
  title: string;
  title_translated: string;
  grams: { [key: string]: number };
  kcal: number;
  macros: { [key: string]: number };
  micros: { [key: string]: number };
  // Legacy fields for backward compatibility
  name?: string;
  calories?: number;
  protein?: number;
  carbs?: number;
  fat?: number;
  fiber?: number;
  serving_size?: string;
  ingredients?: string[];
  meal_type?: string;
}

interface DayMenuData {
  date?: string;
  meals?: MealItem[]; // Real API structure: array of meals
  kcal?: number;
  macros?: { [key: string]: number };
  micros?: { [key: string]: number };
  coverage?: { [key: string]: number };
  tips?: string[];
  total_cost?: number;
  // Legacy fields for backward compatibility with mock data
  total_nutrients?: {
    calories?: number;
    protein?: number;
    carbs?: number;
    fat?: number;
    fiber?: number;
  };
  recommendations?: string[];
  estimated_cost?: number;
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
const MEAL_ORDER_WITH_MISC = ['breakfast', 'lunch', 'dinner', 'snacks', 'misc'] as const;

// Helper function to validate meal item
function isValidMealItem(meal: unknown): meal is MealItem {
  if (!meal || typeof meal !== 'object') {
    return false;
  }

  const typedMeal = meal as { title?: string; name?: string };
  const title = typeof typedMeal.title === 'string' ? typedMeal.title.trim() : '';
  const name = typeof typedMeal.name === 'string' ? typedMeal.name.trim() : '';

  return title.length > 0 || name.length > 0;
}

// Helper function to adapt API data to component expectations
function adaptDayMenuData(dayData: DayMenuData | undefined) {
  if (!dayData) return null;

  // If meals is an array (real API structure), convert to object structure
  if (Array.isArray(dayData.meals)) {
    const mealsArray = dayData.meals;
    const adaptedMeals: { [key: string]: MealItem[] } = {};
    const miscMeals: MealItem[] = []; // Fallback bucket for meals without valid meal_type

    // Group meals by explicit meal_type field or positional inference
    mealsArray.forEach((meal, index) => {
      // Validate meal item first
      if (!isValidMealItem(meal)) {
        console.warn(`Invalid meal item at index ${index}:`, meal);
        return; // Skip invalid entries
      }

      // Convert new structure to legacy structure for compatibility
      const adaptedMeal: MealItem = {
        ...meal,
        name: meal.title || meal.name || 'Unknown Meal',
        calories: meal.kcal ?? meal.calories,
        protein: meal.macros?.protein_g ?? meal.protein,
        carbs: meal.macros?.carbs_g ?? meal.carbs,
        fat: meal.macros?.fat_g ?? meal.fat,
        fiber: meal.macros?.fiber_g ?? meal.fiber,
        // Preserve serving size only when provided by API; avoid hardcoded defaults
        serving_size: meal.serving_size,
        ingredients: meal.ingredients || Object.keys(meal.grams || {}),
      };

      // Check if meal has explicit meal_type and it's valid
      if (meal.meal_type && MEAL_ORDER.includes(meal.meal_type as any)) {
        const mealType = meal.meal_type;
        if (!adaptedMeals[mealType]) {
          adaptedMeals[mealType] = [];
        }
        adaptedMeals[mealType].push(adaptedMeal);
      } else {
        // Fallback: attempt positional inference for first few meals only
        // This is safer than modulo as it only applies to the initial sequence
        if (index < MEAL_ORDER.length) {
          const mealType = MEAL_ORDER[index];
          if (!adaptedMeals[mealType]) {
            adaptedMeals[mealType] = [];
          }
          adaptedMeals[mealType].push(adaptedMeal);

          // Log warning for meals without explicit meal_type
          console.warn(
            `Meal "${meal.title || meal.name || 'Unknown'}" at index ${index} assigned to "${mealType}" due to missing meal_type. ` +
            `Consider adding explicit meal_type field to improve categorization.`
          );
        } else {
          // For meals beyond the initial sequence, put in misc bucket
          miscMeals.push(adaptedMeal);

          // Log warning for meals beyond initial sequence
          console.warn(
            `Meal "${meal.title || meal.name || 'Unknown'}" at index ${index} assigned to "misc" due to missing meal_type and being beyond initial sequence. ` +
            `Consider adding explicit meal_type field to improve categorization.`
          );
        }
      }
    });

    // Add misc meals to a dedicated bucket if any exist
    if (miscMeals.length > 0) {
      adaptedMeals['misc'] = miscMeals;
    }

    return {
      ...dayData,
      meals: adaptedMeals,
      total_calories: dayData.kcal ?? dayData.total_nutrients?.calories ?? dayData.total_calories ?? 0,
      total_protein: dayData.macros?.protein_g ?? dayData.total_nutrients?.protein ?? dayData.total_protein ?? 0,
      total_carbs: dayData.macros?.carbs_g ?? dayData.total_nutrients?.carbs ?? dayData.total_carbs ?? 0,
      total_fat: dayData.macros?.fat_g ?? dayData.total_nutrients?.fat ?? dayData.total_fat ?? 0,
      total_fiber: dayData.macros?.fiber_g ?? dayData.total_nutrients?.fiber ?? dayData.total_fiber ?? 0,
    };
  }

  // If meals is already an object (mock data), use as-is
  return dayData;
}

export function DayMenuCard({ day, dayData, dayIndex }: DayMenuCardProps) {
  const { t } = useTranslation();
  const unitKcal = t('units.kcal', 'kcal');
  const unitGram = t('units.gram', 'g');
  const abbrProtein = t('abbreviations.protein', 'P');
  const abbrCarbs = t('abbreviations.carbs', 'C');
  const abbrFat = t('abbreviations.fat', 'F');

  const normalizedDayIndex = dayIndex >= 0 ? dayIndex : null;
  const dayLabel = day
    ? t(`weeklyPlan.days.${day}`, day)
    : normalizedDayIndex !== null
      ? t('weeklyPlan.dayNumber', 'Day {{number}}', { number: normalizedDayIndex + 1 })
      : t('weeklyPlan.day', 'Day');
  const cardTestId = day
    ? `day-menu-card-${day}`
    : normalizedDayIndex !== null
      ? `day-menu-card-index-${normalizedDayIndex}`
      : 'day-menu-card';
  const dayMenuLabel = t('weeklyPlan.dayMenuLabel', {
    defaultValue: `Daily menu for ${dayLabel}`,
    day: dayLabel,
  });
  const dayHeadingText = t('weeklyPlan.dayMenuHeading', {
    defaultValue: `${dayLabel} meals`,
    day: dayLabel,
  });

  const adaptedData = adaptDayMenuData(dayData);

  if (!adaptedData || !adaptedData.meals || Object.keys(adaptedData.meals).length === 0) {
    return (
      <div className="day-menu-card" data-testid={cardTestId} aria-label={dayLabel}>
        <div className="mb-4">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white capitalize">
            {dayLabel}
          </h3>
          {day && normalizedDayIndex !== null && (
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {t('weeklyPlan.dayPosition', `Day ${normalizedDayIndex + 1}`)}
            </span>
          )}
        </div>
        <div className="p-6 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div className="text-center text-gray-500 dark:text-gray-400">
            <Utensils className="w-8 h-8 mx-auto mb-2" />
            <p>{t('weeklyPlan.noMeals', 'No meals planned for this day')}</p>
          </div>
        </div>
      </div>
    );
  }

  const meals = adaptedData.meals as { [key: string]: MealItem[] };
  const totalCalories = adaptedData.total_calories || 0;

  return (
    <div className="day-menu-card" data-testid={cardTestId} aria-label={dayMenuLabel}>
      <div className="mb-4">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white capitalize">
          {dayHeadingText}
        </h3>
        {normalizedDayIndex !== null && (
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {t('weeklyPlan.dayPosition', 'Day {{number}}', { number: normalizedDayIndex + 1 })}
          </span>
        )}
      </div>

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
            {totalCalories.toLocaleString()} {unitKcal}
          </span>
        </div>

        {/* Macronutrient breakdown */}
        {(adaptedData.total_protein || adaptedData.total_carbs || adaptedData.total_fat) && (
          <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
            {adaptedData.total_protein && (
              <div className="text-center">
                <div className="text-gray-600 dark:text-gray-400">{t('weeklyPlan.protein', 'Protein')}</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {adaptedData.total_protein.toLocaleString()} {unitGram} {abbrProtein}
                </div>
              </div>
            )}
            {adaptedData.total_carbs && (
              <div className="text-center">
                <div className="text-gray-600 dark:text-gray-400">{t('weeklyPlan.carbs', 'Carbs')}</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {adaptedData.total_carbs.toLocaleString()} {unitGram} {abbrCarbs}
                </div>
              </div>
            )}
            {adaptedData.total_fat && (
              <div className="text-center">
                <div className="text-gray-600 dark:text-gray-400">{t('weeklyPlan.fat', 'Fat')}</div>
                <div className="font-semibold text-gray-900 dark:text-white">
                  {adaptedData.total_fat.toLocaleString()} {unitGram} {abbrFat}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Meals */}
      <div className="space-y-4">
        {MEAL_ORDER_WITH_MISC.map((mealType) => {
          const mealItems = meals[mealType];
          if (!mealItems || mealItems.length === 0) return null;

          const mealCalories = mealItems.reduce((sum: number, item: MealItem) => sum + (item.calories || 0), 0);

          return (
            <div
              key={mealType}
              className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
              data-testid={`meal-section-${mealType}`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                  {mealType === 'misc'
                    ? t('weeklyPlan.meals.misc', 'Other Meals')
                    : t(`weeklyPlan.meals.${mealType}`, mealType)
                  }
                </h3>
                <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
                  <Clock className="w-4 h-4" />
                  <span>{mealCalories.toLocaleString()} {unitKcal}</span>
                </div>
              </div>

              <div className="space-y-3">
                {mealItems.map((item: MealItem, index: number) => (
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
                          {item.calories.toLocaleString()} {unitKcal}
                        </div>
                      )}
                      {(item.protein || item.carbs || item.fat) && (
                        <div className="text-gray-600 dark:text-gray-400">
                          {[
                            item.protein ? `${item.protein}${unitGram} ${abbrProtein}` : null,
                            item.carbs ? `${item.carbs}${unitGram} ${abbrCarbs}` : null,
                            item.fat ? `${item.fat}${unitGram} ${abbrFat}` : null,
                          ]
                            .filter((part): part is string => Boolean(part))
                            .join(' • ')}
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

    </div>
  );
}
