/**
 * Weekly Plan Data Models
 *
 * Strict typing for API contract and view models to prevent contract drift.
 */

/** Raw API response from backend (POST /api/v1/pro/meal/weekly) */
export interface RawWeekPlanResponse {
  daily_menus: Array<Record<string, unknown>>;
  weekly_coverage: Record<string, unknown>;
  shopping_list: Record<string, unknown>;
  total_cost: number;
  adherence_score: number;
}

/** Normalized meal data */
export interface Meal {
  meal_type: string; // "breakfast" | "lunch" | "dinner" | "snack"
  recipes: Array<{
    id: string;
    name: string;
    portions: number;
  }>;
  totals: {
    kcal: number;
    protein_g?: number;
    fat_g?: number;
    carbs_g?: number;
    fiber_g?: number;
  };
}

/** Normalized day data */
export interface DayMenu {
  day: number; // 1-7
  dayName?: string; // "Monday", "Tuesday", etc.
  meals: Meal[];
  daily_totals: {
    kcal: number;
    protein_g: number;
    fat_g: number;
    carbs_g: number;
    fiber_g: number;
  };
}

/** View Model for Weekly Plan (normalized, safe for UI consumption) */
export interface WeekPlanVM {
  days: DayMenu[];
  weekly_coverage: {
    protein: number; // percentage
    iron: number;
    vitamin_c: number;
    calcium: number;
    [key: string]: number;
  };
  metrics: {
    total_cost: number;
    adherence_score: number; // 0.0 - 1.0
  };
  meta: {
    total_days: number;
    has_incomplete_data: boolean; // true if any normalization fallbacks triggered
  };
}

/** Loading/error states for UI */
export type WeekPlanState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: WeekPlanVM };
