import type { StoryObj } from "@storybook/react";
import WaterCard from "./WaterCard";

const meta = {
  title: "Nutrition/WaterCard",
  component: WaterCard,
  args: {
    liters: 2.5,
  },
  argTypes: {
    liters: {
      control: { type: "number", min: 0, max: 5, step: 0.1 },
      description: "Daily water intake recommendation in liters",
    },
  },
};

export default meta;

export const Default: StoryObj<typeof WaterCard> = {};

export const LowIntake: StoryObj<typeof WaterCard> = {
  args: {
    liters: 1.5,
  },
};

export const HighIntake: StoryObj<typeof WaterCard> = {
  args: {
    liters: 4.0,
  },
};

export const Athlete: StoryObj<typeof WaterCard> = {
  args: {
    liters: 3.5,
  },
};
