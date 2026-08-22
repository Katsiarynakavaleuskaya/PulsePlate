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
      { method: "POST", body: body as any, signal: options?.signal },
      options?.onAuthError ? { onAuthError: options.onAuthError } : undefined,
      true // explicitly force JSON Content-Type for Premium POSTs
    );
}

export type BmrRequest = components["schemas"]["BMRRequest"];
export type BmrApiResponse = components["schemas"]["BMRResponse"];

export type Portion = {
  protein_palm: number;
  fat_thumbs: number;
  carb_cups: number;
  veg_cups: number;
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

// OpenAPI generated types
export type PlateRequest = components["schemas"]["PlateRequest"];
export type PlateResponse = components["schemas"]["PlateResponse"];

export type PlateApiResponse = {
  kcal: number;
  macros: Record<string, number>;
  portions: Portion;
  layout: LayoutItem[];
  meals: Meal[];
  day_micros?: Record<string, number>;
  meals_per_day: number; // Metadata: number of meals per day
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
