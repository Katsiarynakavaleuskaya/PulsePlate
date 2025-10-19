// Mock type for testing - using local type to avoid circular dependencies
type SetupFormValues = {
  sex: "male" | "female";
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: "active" | "sedentary" | "light" | "moderate" | "athlete";
  goal: "lose" | "maintain" | "gain";
  life_stage: "child" | "adult" | "elderly";
  lang: string;
  diet_flags: ("VEG" | "GF" | "DAIRY_FREE" | "LOW_COST" | "HIGH_PROTEIN" | "LOW_CARB" | "KETO" | "PALEO" | "MEDITERRANEAN" | "VEGAN")[];
};

export const mockValues: SetupFormValues = {
  sex: "female" as const,
  age: 30,
  height_cm: 170,
  weight_kg: 65,
  activity: "moderate" as const,
  goal: "maintain" as const,
  life_stage: "adult" as const,
  lang: "en",
  diet_flags: [],
};
