import type { StoryObj, Meta } from "@storybook/react";
import MicrosGrid from "./MicrosGrid";

const sampleItems = [
  { id: "iron", name: "Iron", unit: "mg", target: 18 },
  { id: "calcium", name: "Calcium", unit: "mg", target: 1000 },
  { id: "vitamin_d", name: "Vitamin D", unit: "IU", target: 600 },
  { id: "vitamin_b12", name: "Vitamin B12", unit: "μg", target: 2.4 },
  { id: "folate", name: "Folate", unit: "μg", target: 400 },
  { id: "iodine", name: "Iodine", unit: "μg", target: 150 },
  { id: "potassium", name: "Potassium", unit: "mg", target: 4700 },
  { id: "magnesium", name: "Magnesium", unit: "mg", target: 400 },
];

const meta: Meta<typeof MicrosGrid> = {
  title: "Nutrition/MicrosGrid",
  component: MicrosGrid,
  args: {
    items: sampleItems,
  },
};

export default meta;

export const Default: StoryObj<typeof MicrosGrid> = {};

export const Empty: StoryObj<typeof MicrosGrid> = {
  args: {
    items: [],
  },
};

export const FewItems: StoryObj<typeof MicrosGrid> = {
  args: {
    items: sampleItems.slice(0, 3),
  },
};

export const ManyItems: StoryObj<typeof MicrosGrid> = {
  args: {
    items: [
      ...sampleItems,
      { id: "zinc", name: "Zinc", unit: "mg", target: 11 },
      { id: "copper", name: "Copper", unit: "mg", target: 0.9 },
      { id: "selenium", name: "Selenium", unit: "μg", target: 55 },
    ],
  },
};
