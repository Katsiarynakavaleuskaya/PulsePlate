/**
 * Type definitions for Weekly Plan API responses
 * These interfaces match the backend response structure from /api/v1/premium/plan/week
 */

export interface MealItem {
  product_name: string;
  category?: string;
  amount?: number;
  unit?: string;
  calories?: number;
  protein_g?: number;
  fat_g?: number;
  carbs_g?: number;
  [key: string]: unknown; // Allow additional properties
}

export interface Meal {
  meal_type: string;
  time?: string;
  items: MealItem[];
  total_calories?: number;
  [key: string]: unknown; // Allow additional properties
}

export interface DailyMenu {
  day_name: string;
  date?: string;
  meals: Meal[];
  daily_totals?: {
    calories?: number;
    protein_g?: number;
    fat_g?: number;
    carbs_g?: number;
  };
  [key: string]: unknown; // Allow additional properties
}

export interface WeekPlanData {
  daily_menus: DailyMenu[];
  week_totals?: {
    calories?: number;
    protein_g?: number;
    fat_g?: number;
    carbs_g?: number;
  };
  [key: string]: unknown; // Allow additional properties
}
