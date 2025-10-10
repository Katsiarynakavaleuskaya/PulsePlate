import type { Meta, StoryFn, StoryObj } from "@storybook/react";
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import WaterCard from "./WaterCard";

const meta = {
  title: "Nutrition/WaterCard",
  component: WaterCard,
  decorators: [
    (Story: StoryFn) => (
      <I18nextProvider i18n={i18n}>
        <Story />
      </I18nextProvider>
    ),
  ],
  args: {
    liters: 2.5,
  },
  argTypes: {
    liters: {
      control: { type: "number", min: 0, max: 5, step: 0.1 },
      description: "Daily water intake recommendation in liters",
    },
  },
} satisfies Meta<typeof WaterCard>;

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
