import type { Meta, StoryObj } from '@storybook/react';
import '../i18n';
import NutritionSetupPage from './NutritionSetup';
import {
  NutritionSetupFormStorySurface,
  NutritionSetupResultStorySurface,
} from '../stories/storybookParitySupport';

const meta = {
  title: 'PulsePlate/Parity Pack/Nutrition Setup',
  component: NutritionSetupPage,
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta<typeof NutritionSetupPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ProfileForm: Story = {
  render: () => <NutritionSetupFormStorySurface />,
};

export const CalculatedResults: Story = {
  render: () => <NutritionSetupResultStorySurface />,
};
