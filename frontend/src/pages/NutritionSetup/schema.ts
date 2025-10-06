// RU: Схемы типов и валидации для Nutrition Setup
// EN: Type schemas and validation for Nutrition Setup

import { z } from "zod";

// Valid diet flags enum
const validDietFlags = [
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

export type BmrResponse = {
  bmr: number;
  method: string;
};

export type EnrichedBmrResponse = BmrResponse & {
  tdee: number;
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
  water_l: number;
};

export type TargetsResponse = {
  micros: Array<{
    id: string;
    name: string;
    unit: string;
    target: number;
  }>;
};
