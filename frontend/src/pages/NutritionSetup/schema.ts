// RU: Схемы типов и валидации для Nutrition Setup
// EN: Type schemas and validation for Nutrition Setup

import { z } from "zod";

/**
 * Valid diet flags that can be selected in the UI.
 * Note: Not all flags are currently supported by the backend API.
 * See SUPPORTED_DIET_FLAGS in hooks.ts for the subset that works.
 */
export const validDietFlags = [
  "VEG", "GF", "DAIRY_FREE", "LOW_COST", "HIGH_PROTEIN",
  "LOW_CARB", "KETO", "PALEO", "MEDITERRANEAN", "VEGAN"
] as const;

export const setupSchema = z.object({
  sex: z.enum(["male", "female"]),
  age: z.number().int().min(13).max(90),
  height_cm: z.number().min(120).max(230),
  weight_kg: z.number().min(30).max(300),
  activity: z.enum(["sedentary", "light", "moderate", "active", "athlete"]),
  goal: z.enum(["lose", "maintain", "gain"]),
  diet_flags: z.array(z.enum(validDietFlags)).default([]),
});

export type SetupFormValues = z.infer<typeof setupSchema>;
export type DietFlag = typeof validDietFlags[number];

export const isValidSetupFormValues = (data: unknown): data is SetupFormValues =>
  setupSchema.safeParse(data).success;

export type NormalizedBmrMethod =
  | "Mifflin-St Jeor"
  | "Harris-Benedict"
  | "Katch-McArdle"
  | "BMR"
  | "stub";

/**
 * Normalized BMR data for UI display.
 * This is a simplified representation of BmrApiResponse from the premium API,
 * containing the most relevant values (single BMR and TDEE numbers) for user display.
 */
export type NormalizedBmrData = {
  bmr: number;
  tdee: number;
  method: NormalizedBmrMethod;
};

export type PlateResponse = {
  plate: {
    carbs_pct: number;
    protein_pct: number;
    fat_pct: number;
    kcal: number;
  };
  macros: {
    carbs_g: number;
    protein_g: number;
    fat_g: number;
    fiber_g: number;
  };
  water_l: number | null;
};

export type TargetsResponse = {
  micros: Array<{
    id: string;
    name: string;
    unit: string;
    target: number;
  }>;
  water_l: number | null;
};
