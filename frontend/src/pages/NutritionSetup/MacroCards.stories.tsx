import type { Meta, StoryObj } from "@storybook/react";
import MacroCards from "./MacroCards";

const meta = {
  title: "Nutrition/MacroCards",
  component: MacroCards,
  args: {
    kcal: 2200,
    carbsG: 275,
    proteinG: 110,
    fatG: 73,
    fiberG: 30,
    bmr: 1600,
    tdee: 2200,
  },
  argTypes: {
    kcal: {
      control: { type: "number", min: 1000, max: 5000 },
      description: "Daily calorie target",
    },
    carbsG: {
      control: { type: "number", min: 0, max: 500 },
      description: "Carbohydrates in grams",
    },
    proteinG: {
      control: { type: "number", min: 0, max: 300 },
      description: "Protein in grams",
    },
    fatG: {
      control: { type: "number", min: 0, max: 200 },
      description: "Fat in grams",
    },
    fiberG: {
      control: { type: "number", min: 0, max: 100 },
      description: "Fiber in grams",
    },
    bmr: {
      control: { type: "number", min: 1000, max: 3000 },
      description: "Basal Metabolic Rate",
    },
    tdee: {
      control: { type: "number", min: 1000, max: 5000 },
      description: "Total Daily Energy Expenditure",
    },
  },
};

export default meta;

export const Default: StoryObj<typeof MacroCards> = {};

export const HighProtein: StoryObj<typeof MacroCards> = {
  args: {
    kcal: 2500,
    carbsG: 200,
    proteinG: 200,
    fatG: 80,
    fiberG: 35,
    bmr: 1700,
    tdee: 2500,
  },
};

export const Keto: StoryObj<typeof MacroCards> = {
  args: {
    kcal: 1800,
    carbsG: 50,
    proteinG: 100,
    fatG: 120,
    fiberG: 25,
    bmr: 1500,
    tdee: 1800,
  },
};
