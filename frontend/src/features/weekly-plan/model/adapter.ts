/**
 * Weekly Plan Adapter
 *
 * Normalizes raw API response into safe, type-strict view model.
 * Prevents contract drift by providing sensible defaults for missing/malformed data.
 */

import type { RawWeekPlanResponse, WeekPlanVM, DayMenu, Meal } from './types';

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

/**
 * Safely extract number from unknown value
 */
function safeNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  return fallback;
}

/**
 * Safely extract string from unknown value
 */
function safeString(value: unknown, fallback = ''): string {
  if (typeof value === 'string') {
    return value;
  }
  return fallback;
}

/**
 * Log contract drift warning in development
 */
function logContractDrift(context: string, details?: string): void {
  if (import.meta.env.DEV) {
    const message = details
      ? `[WeekPlan Adapter] ${context}: ${details}`
      : `[WeekPlan Adapter] ${context}`;
    console.warn(message);
  }
}

/**
 * Normalize a single meal from raw data
 */
function normalizeMeal(raw: Record<string, unknown>): Meal {
  const recipes = Array.isArray(raw.recipes)
    ? raw.recipes
        .filter(
          (r): r is Record<string, unknown> =>
            r != null && typeof r === 'object' && !Array.isArray(r)
        )
        .map((r) => ({
          id: safeString(r.id, 'unknown'),
          name: safeString(r.name, 'Unnamed Recipe'),
          portions: safeNumber(r.portions, 1),
        }))
    : [];

  const totals = raw.totals as Record<string, unknown> | undefined;

  return {
    meal_type: safeString(raw.meal_type, 'meal'),
    recipes,
    totals: {
      kcal: safeNumber(totals?.kcal),
      protein_g: safeNumber(totals?.protein_g),
      fat_g: safeNumber(totals?.fat_g),
      carbs_g: safeNumber(totals?.carbs_g),
      fiber_g: safeNumber(totals?.fiber_g),
    },
  };
}

/**
 * Normalize a single day menu from raw data
 */
function normalizeDayMenu(raw: Record<string, unknown>, index: number): DayMenu {
  const dayNumber = Math.max(1, safeNumber(raw.day, index + 1));
  const meals = Array.isArray(raw.meals)
    ? raw.meals
        .filter((m): m is Record<string, unknown> => m != null && typeof m === 'object' && !Array.isArray(m))
        .map(normalizeMeal)
    : [];

  // Calculate daily totals from meals if not provided
  const dailyTotals = raw.daily_totals as Record<string, unknown> | undefined;
  const calculatedTotals = meals.reduce(
    (acc, meal) => ({
      kcal: acc.kcal + (meal.totals.kcal || 0),
      protein_g: acc.protein_g + (meal.totals.protein_g || 0),
      fat_g: acc.fat_g + (meal.totals.fat_g || 0),
      carbs_g: acc.carbs_g + (meal.totals.carbs_g || 0),
      fiber_g: acc.fiber_g + (meal.totals.fiber_g || 0),
    }),
    { kcal: 0, protein_g: 0, fat_g: 0, carbs_g: 0, fiber_g: 0 }
  );

  return {
    day: dayNumber,
    dayName: DAY_NAMES[(dayNumber - 1) % 7],
    meals,
    daily_totals: {
      kcal: safeNumber(dailyTotals?.kcal, calculatedTotals.kcal),
      protein_g: safeNumber(dailyTotals?.protein_g, calculatedTotals.protein_g),
      fat_g: safeNumber(dailyTotals?.fat_g, calculatedTotals.fat_g),
      carbs_g: safeNumber(dailyTotals?.carbs_g, calculatedTotals.carbs_g),
      fiber_g: safeNumber(dailyTotals?.fiber_g, calculatedTotals.fiber_g),
    },
  };
}

/**
 * Normalize weekly coverage data
 */
function normalizeWeeklyCoverage(raw: Record<string, unknown>): WeekPlanVM['weekly_coverage'] {
  return {
    protein: safeNumber(raw.protein, 0),
    iron: safeNumber(raw.iron, 0),
    vitamin_c: safeNumber(raw.vitamin_c, 0),
    calcium: safeNumber(raw.calcium, 0),
    ...Object.fromEntries(
      Object.entries(raw)
        .filter(([key]) => !['protein', 'iron', 'vitamin_c', 'calcium'].includes(key))
        .map(([key, value]) => [key, safeNumber(value, 0)])
    ),
  };
}

/**
 * Normalize raw API response into view model
 *
 * @param raw - Raw API response
 * @returns Normalized view model safe for UI consumption
 */
export function normalizeWeekPlan(raw: RawWeekPlanResponse): WeekPlanVM {
  let hasIncompleteData = false;

  // Normalize days
  const days = Array.isArray(raw.daily_menus)
    ? raw.daily_menus.map((menu, index) => {
        if (!menu || typeof menu !== 'object') {
          hasIncompleteData = true;
          logContractDrift('Incomplete data detected', `day ${index + 1}: invalid menu object`);
          return normalizeDayMenu({}, index);
        }
        return normalizeDayMenu(menu, index);
      })
    : (() => {
        if (raw.daily_menus !== undefined) {
          hasIncompleteData = true;
          logContractDrift('Invalid daily_menus', 'expected array, using empty');
        }
        return [];
      })();

  // Log contract drift summary
  if (hasIncompleteData) {
    logContractDrift('API response contains incomplete or malformed data');
  }

  // Normalize coverage
  let weekly_coverage: WeekPlanVM['weekly_coverage'];
  if (raw.weekly_coverage && typeof raw.weekly_coverage === 'object') {
    weekly_coverage = normalizeWeeklyCoverage(raw.weekly_coverage);
  } else {
    hasIncompleteData = true;
    logContractDrift('Missing weekly_coverage', 'using default values');
    weekly_coverage = { protein: 0, iron: 0, vitamin_c: 0, calcium: 0 };
  }

  return {
    days,
    weekly_coverage,
    metrics: {
      total_cost: safeNumber(raw.total_cost, 0),
      adherence_score: Math.min(1, Math.max(0, safeNumber(raw.adherence_score, 0))),
    },
    meta: {
      total_days: days.length,
      has_incomplete_data: hasIncompleteData,
    },
  };
}
