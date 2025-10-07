export type PremiumRequestOptions = {
  navigate?: (path: string) => void;
  signal?: AbortSignal;
};

export type BmrRequest = {
  sex: 'male' | 'female';
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: 'sedentary' | 'light' | 'moderate' | 'active' | 'very_active';
  bodyfat?: number | null;
  lang?: string;
};

export type BmrApiResponse = {
  bmr: Record<string, number>;
  tdee: Record<string, number>;
  activity_level: string;
  recommended_intake: Record<string, number>;
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
  portions: Record<string, unknown>;
  layout: Array<Record<string, unknown>>;
  meals: Array<Record<string, unknown>>;
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
