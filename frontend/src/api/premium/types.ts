import { api, ApiOptions } from '../client';
import type { components } from '../schema';

export type SupportedPremiumLang = 'ru' | 'en' | 'es';

export type PremiumRequestOptions = Pick<ApiOptions, "onAuthError"> & { signal?: AbortSignal };

/**
 * Factory to build typed Premium endpoints (POST).
 * Body should be a plain object (api() serializes JSON internally).
 * onAuthError is forwarded as api() options (3rd arg).
 */
export function createPremiumEndpoint<TReq, TRes>(endpoint: string) {
  return (body: TReq, options?: PremiumRequestOptions) =>
    api<TRes>(
      endpoint,
      { method: "POST", body: JSON.stringify(body), signal: options?.signal },
      options?.onAuthError ? { onAuthError: options.onAuthError } : undefined,
      true // explicitly force JSON Content-Type for Premium POSTs
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
  method?: string;
};

// OpenAPI generated types
export type PlateRequest = components["schemas"]["PlateRequest"];

export type PlateApiResponse = {
  kcal: number;
  macros: Record<string, number>;
  portions: Portion;
  layout: LayoutItem[];
  meals: Meal[];
  day_micros?: Record<string, number>;
};

// OpenAPI generated types
export type TargetsRequest = components["schemas"]["WHOTargetsRequest"];

export type TargetsApiResponse = {
  kcal_daily: number;
  macros: Record<string, number>;
  water_ml: number;
  priority_micros: Record<string, number>;
  activity_weekly: Record<string, number>;
  calculation_date: string;
  warnings: Array<Record<string, string>>;
};
