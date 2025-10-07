import { api } from '../client';

export type SupportedPremiumLang = 'ru' | 'en' | 'es';

export type PremiumRequestOptions = {
  navigate?: (path: string) => void;
  signal?: AbortSignal;
};

/**
 * Generic factory for creating premium API endpoints that use POST requests
 * @param endpoint - The API endpoint path (e.g., '/api/v1/premium/plate')
 * @returns A function that takes request body and options, and returns a Promise of the response
 */
export function createPremiumEndpoint<TReq, TRes>(endpoint: string) {
  return (body: TReq, options?: PremiumRequestOptions) =>
    api<TRes>(
      endpoint,
      { method: 'POST', body: JSON.stringify(body), signal: options?.signal },
      options?.navigate,
      true,
    );
}

export type BmrRequest = {
  sex: 'male' | 'female';
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';
  bodyfat?: number | null;
  lang?: SupportedPremiumLang | string;
};

export type BmrValues = {
  mifflin: number;
  harris: number;
  katch?: number;
};

export type TdeeValues = {
  mifflin: number;
  harris: number;
  katch?: number;
};

export type RecommendedIntake = {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
};

export type Portion = {
  protein_palm: number;
  fat_thumbs: number;
  carb_cups: number;
  veg_cups: number;
  meals_per_day: number;
};

export type LayoutItem = {
  kind: 'plate_sector' | 'bowl' | 'marker';
  fraction: number;
  label: string;
  tooltip: string;
};

export type Meal = {
  title: string;
  kcal: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  micros?: Record<string, number>;
};

export type BmrApiResponse = {
  bmr: BmrValues;
  tdee: TdeeValues;
  activity_level: string;
  recommended_intake: RecommendedIntake;
  formulas_used: string[];
  notes: string[];
};

export type PlateRequest = {
  sex: 'male' | 'female';
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';
  goal: 'loss' | 'maintain' | 'gain';
  deficit_pct?: number | null;
  surplus_pct?: number | null;
  bodyfat?: number | null;
  diet_flags?: string[] | null;
};

export type PlateApiResponse = {
  kcal: number;
  macros: Record<string, number>;
  portions: Portion;
  layout: LayoutItem[];
  meals: Meal[];
  day_micros?: Record<string, number>;
};

export type TargetsRequest = {
  sex: 'male' | 'female';
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';
  goal?: 'loss' | 'maintain' | 'gain';
  deficit_pct?: number | null;
  surplus_pct?: number | null;
  bodyfat?: number | null;
  diet_flags?: string[] | null;
  life_stage?: 'child' | 'teen' | 'adult' | 'pregnant' | 'lactating' | 'elderly';
  lang?: string;
};

export type TargetsApiResponse = {
  kcal_daily: number;
  macros: Record<string, number>;
  water_ml: number;
  priority_micros: Record<string, number>;
  activity_weekly: Record<string, number>;
  calculation_date: string;
  warnings: Array<Record<string, string>>;
};
