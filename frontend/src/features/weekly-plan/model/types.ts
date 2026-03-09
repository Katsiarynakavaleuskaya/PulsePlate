/**
 * Weekly plan view-model types derived from the canonical OpenAPI contract.
 */

import type { WeeklyMenuResponse } from '../../../api/premium/weekly-plan';

export type RawWeekPlanResponse = WeeklyMenuResponse;
export type RawDayMenu = RawWeekPlanResponse['daily_menus'][number];
export type RawMeal = RawDayMenu['meals'][number];

/** Normalized meal data for UI consumption. */
export interface Meal {
  title: string;
  title_translated: string;
  kcal: number;
  price_est: number | null;
  grams: Record<string, number>;
  macros: Record<string, number>;
  micros: Record<string, number>;
}

/** Normalized day data for UI consumption. */
export interface DayMenu {
  day: number;
  dayName: string;
  meals: Meal[];
  kcal: number;
  macros: Record<string, number>;
  micros: Record<string, number>;
  coverage: Record<string, number>;
  tips: string[];
  total_cost: number;
}

/** View model for weekly plan screen. */
export interface WeekPlanVM {
  days: DayMenu[];
  weekly_coverage: {
    protein: number;
    iron: number;
    vitamin_c: number;
    calcium: number;
    [key: string]: number;
  };
  shopping_list: Record<string, number>;
  metrics: {
    total_cost: number;
    adherence_score: number;
  };
  meta: {
    total_days: number;
    has_incomplete_data: boolean;
  };
}

/** Loading/error states for UI. */
export type WeekPlanState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: WeekPlanVM };
