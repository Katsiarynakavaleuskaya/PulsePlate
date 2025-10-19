// import type { SetupFormValues } from "../schema";

// Mock type for testing
type SetupFormValues = {
  sex: string;
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: string;
  goal: string;
  life_stage: string;
  lang: string;
  diet_flags?: string[];
};

export const mockValues: SetupFormValues = {
  sex: "female",
  age: 30,
  height_cm: 170,
  weight_kg: 65,
  activity: "moderate",
  goal: "maintain",
  life_stage: "adult",
  lang: "en",
  diet_flags: [],
};
