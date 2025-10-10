import type { Meta, StoryFn, StoryObj } from "@storybook/react";
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import PlateChart from "./PlateChart";

const meta = {
  title: "Nutrition/PlateChart",
  component: PlateChart,
  decorators: [
    (Story: StoryFn) => (
      <I18nextProvider i18n={i18n}>
        <Story />
      </I18nextProvider>
    ),
  ],
  args: {
    carbsPct: 45,
    proteinPct: 25,
    fatPct: 30,
  },
  argTypes: {
    carbsPct: {
      control: { type: "range", min: 0, max: 100 },
      description: "Percentage of carbohydrates. Values should sum to 100%.",
    },
    proteinPct: {
      control: { type: "range", min: 0, max: 100 },
      description: "Percentage of protein. Values should sum to 100%.",
    },
    fatPct: {
      control: { type: "range", min: 0, max: 100 },
      description: "Percentage of fat. Values should sum to 100%.",
    },
  },
} satisfies Meta<typeof PlateChart>;

export default meta;

export const Default: StoryObj<typeof PlateChart> = {};

export const HighProtein: StoryObj<typeof PlateChart> = {
  args: {
    carbsPct: 30,
    proteinPct: 50,
    fatPct: 20,
  },
};

export const Keto: StoryObj<typeof PlateChart> = {
  args: {
    carbsPct: 10,
    proteinPct: 20,
    fatPct: 70,
  },
};

export const Balanced: StoryObj<typeof PlateChart> = {
  args: {
    carbsPct: 40,
    proteinPct: 30,
    fatPct: 30,
  },
};

export const InvalidSum: StoryObj<typeof PlateChart> = {
  args: {
    carbsPct: 50,
    proteinPct: 50,
    fatPct: 50,
  },
};
