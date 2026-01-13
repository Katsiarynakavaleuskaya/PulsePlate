/** @vitest-environment jsdom */
import { describe, it, expect, expectTypeOf } from "vitest";
import type { Portion, LayoutItem, Meal } from "../types";
import type { components } from "../../schema";

type PlateResponse = components["schemas"]["PlateResponse"];

describe("Premium Types", () => {
  describe("Portion", () => {
    it("should accept valid portion data", () => {
      const validPortion: Portion = {
        protein_palm: 2.5,
        fat_thumbs: 1.8,
        carb_cups: 3.2,
        veg_cups: 2.0,
      };
      expect(validPortion).toBeDefined();
    });

    it("should enforce required fields on Portion (type-level)", () => {
      const valid: Portion = {
        protein_palm: 2.5,
        fat_thumbs: 1.8,
        carb_cups: 3.2,
        veg_cups: 2.0,
      };
      expectTypeOf(valid).toMatchTypeOf<Portion>();
    });
  });

  describe("LayoutItem", () => {
    it("should accept valid layout item", () => {
      const validLayoutItem: LayoutItem = {
        kind: "plate_sector",
        fraction: 0.35,
        label: "Protein",
        tooltip: "Lean protein sources",
      };
      expect(validLayoutItem).toBeDefined();
    });

    it("should only accept valid kinds", () => {
      const validKinds: Array<LayoutItem["kind"]> = ["plate_sector", "bowl", "marker"];

      validKinds.forEach(kind => {
        const item: LayoutItem = {
          kind,
          fraction: 0.5,
          label: "Test",
          tooltip: "Test tooltip",
        };
        expect(item.kind).toBe(kind);
      });
    });
  });

  describe("Meal", () => {
    it("should accept valid meal data", () => {
      const validMeal: Meal = {
        title: "Breakfast",
        kcal: 450,
        protein_g: 25,
        fat_g: 15,
        carbs_g: 50,
      };
      expect(validMeal).toBeDefined();
    });

    it("should accept meal data with micros", () => {
      const validMealWithMicros: Meal = {
        title: "Breakfast",
        kcal: 450,
        protein_g: 25,
        fat_g: 15,
        carbs_g: 50,
        micros: {
          iron_mg: 2.5,
          calcium_mg: 150,
          vitamin_c_mg: 25,
        },
      };
      expect(validMealWithMicros).toBeDefined();
    });
  });

  describe("PlateResponse (OpenAPI)", () => {
    it("should accept valid plate API response (OpenAPI schema)", () => {
      const validResponse: PlateResponse = {
        kcal: 2000,
        macros: {
          protein_g: 125,
          fat_g: 67,
          carbs_g: 250,
        },
        portions: {
          protein_palm: 2.1,
          fat_thumbs: 1.3,
          carb_cups: 4.2,
          veg_cups: 3.0,
        },
        meals_per_day: 3,
        layout: [
          {
            kind: "plate_sector",
            fraction: 0.35,
            label: "Protein",
            tooltip: "Lean protein",
          },
          {
            kind: "plate_sector",
            fraction: 0.40,
            label: "Carbs",
            tooltip: "Whole grains",
          },
          {
            kind: "plate_sector",
            fraction: 0.20,
            label: "Vegetables",
            tooltip: "Non-starchy veg",
          },
          {
            kind: "plate_sector",
            fraction: 0.05,
            label: "Fats",
            tooltip: "Healthy fats",
          },
        ],
        meals: [
          {
            title: "Breakfast",
            kcal: 600,
            protein_g: 30,
            fat_g: 20,
            carbs_g: 75,
          },
          {
            title: "Lunch",
            kcal: 700,
            protein_g: 40,
            fat_g: 25,
            carbs_g: 80,
          },
          {
            title: "Dinner",
            kcal: 700,
            protein_g: 40,
            fat_g: 25,
            carbs_g: 80,
          },
        ],
        day_micros: {
          iron_mg: 7.5,
          calcium_mg: 450,
        },
      };
      expect(validResponse).toBeDefined();
      expect(validResponse.kcal).toBe(2000);
      expect(validResponse.macros).toBeDefined();
      expect(validResponse.portions).toBeDefined();
    });

    it("should enforce PlateResponse required fields (type-level)", () => {
      const sample: PlateResponse = {
        kcal: 2000,
        macros: {
          protein_g: 125,
          fat_g: 67,
          carbs_g: 250,
        },
        portions: {
          protein_palm: 2.1,
          fat_thumbs: 1.3,
          carb_cups: 4.2,
          veg_cups: 3.0,
        },
        meals_per_day: 3,
        layout: [],
        meals: [],
      };
      expectTypeOf(sample).toMatchTypeOf<PlateResponse>();
    });
  });
});
