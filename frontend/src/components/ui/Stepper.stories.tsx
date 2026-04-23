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
    ariaLabel: 'Setup progress',
    currentStep: 1,
    progressLabel: 'Step 2 of 2',
    steps: [
      { id: 'profile', label: 'Profile', description: 'Capture your nutrition inputs' },
      { id: 'results', label: 'Results', description: 'Review macros and targets' },
    ],
  },
};
