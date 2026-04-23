import type { Meta, StoryObj } from '@storybook/react';
import { Stepper } from './Stepper';

const meta: Meta<typeof Stepper> = {
  title: 'HPP/Stepper',
  component: Stepper,
};

export default meta;
type Story = StoryObj<typeof Stepper>;

export const NutritionSetupFlow: Story = {
  args: {
    currentStep: 1,
    steps: [
      { id: 'profile', label: 'Profile', description: 'Capture your nutrition inputs' },
      { id: 'results', label: 'Results', description: 'Review macros and targets' },
    ],
  },
};
