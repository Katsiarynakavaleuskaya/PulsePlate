// RU: Схемы типов и валидации для Nutrition Setup
// EN: Type schemas and validation for Nutrition Setup

import { z } from "zod";

/**
 * Valid diet flags that can be selected in the UI.
 * All flags are supported by the backend API as of Oct 2025.
 *
 * Backend-supported flags (actively processed):
 * - HIGH_PROTEIN, LOW_CARB, MEDITERRANEAN: Adjust macro calculations
 * - VEG, GF, DAIRY_FREE, LOW_COST: Used in recipe/food filtering
 * - VEGAN, KETO, PALEO: Normalized to other flags (VEGAN→VEG, KETO→LOW_CARB+HIGH_PROTEIN, PALEO→HIGH_PROTEIN)
 *
 * Note: SUPPORTED_DIET_FLAGS in hooks.ts includes all validDietFlags.
 */
export const validDietFlags = [
  "VEG", "GF", "DAIRY_FREE", "LOW_COST", "HIGH_PROTEIN",
  "LOW_CARB", "KETO", "PALEO", "MEDITERRANEAN", "VEGAN"
] as const;

export const setupSchema = z.object({
  sex: z.enum(["male", "female"]),
  age: z.number({ error: "Required" })
    .int({ error: "Expected integer, received float" })
    .min(13, { error: "Number must be greater than or equal to 13" })
    .max(90, { error: "Number must be less than or equal to 90" }),
  height_cm: z.number({ error: "Required" })
    .min(120, { error: "Number must be greater than or equal to 120" })
    .max(230, { error: "Number must be less than or equal to 230" }),
  weight_kg: z.number({ error: "Required" })
    .min(30, { error: "Number must be greater than or equal to 30" })
    .max(300, { error: "Number must be less than or equal to 300" }),
  activity: z.enum(["sedentary", "light", "moderate", "active", "athlete"]),
  goal: z.enum(["lose", "maintain", "gain"]),
  diet_flags: z.array(z.enum(validDietFlags)).max(validDietFlags.length).default([]),
});

export type SetupFormInput = z.input<typeof setupSchema>;
export type SetupFormValues = z.output<typeof setupSchema>;
export type DietFlag = typeof validDietFlags[number];

export const parseSetupFormValues = (data: unknown): SetupFormValues | undefined => {
  const result = setupSchema.safeParse(data);
  return result.success ? result.data : undefined;
};

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
