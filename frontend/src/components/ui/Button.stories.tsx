import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta = {
  title: 'HPP/Button',
  component: Button,
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    children: 'Continue',
    variant: 'primary',
  },
};

export const Secondary: Story = {
  args: {
    children: 'Back',
    variant: 'secondary',
  },
};

export const Ghost: Story = {
  args: {
    children: 'Skip',
    variant: 'ghost',
  },
};

export const Success: Story = {
  args: {
    children: 'Saved',
    variant: 'success',
  },
};

export const Warning: Story = {
  args: {
    children: 'Review',
    variant: 'warning',
  },
};

export const Destructive: Story = {
  args: {
    children: 'Remove',
    variant: 'destructive',
  },
};

export const Loading: Story = {
  args: {
    children: 'Submit payment',
    loading: true,
    loadingLabel: 'Processing…',
    variant: 'primary',
  },
};

export const Sizes: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <Button size="sm">Small</Button>
      <Button size="md">Medium</Button>
      <Button size="lg">Large</Button>
    </div>
  ),
};
