import type { Meta, StoryObj } from '@storybook/react';
import { StatsCard } from './StatsCard';

const meta: Meta<typeof StatsCard> = {
  title: 'HPP/StatsCard',
  component: StatsCard,
};

export default meta;
type Story = StoryObj<typeof StatsCard>;

export const Default: Story = {
  args: {
    detail: 'Server-side reliability lane',
    label: 'AI quota',
    value: 'Ready',
  },
};

export const Inverse: Story = {
  args: {
    detail: 'Access to guided features',
    label: 'Premium',
    tone: 'inverse',
    value: 'Active',
  },
  render: (args) => (
    <div className="max-w-xs bg-[var(--pp-navy)] p-6">
      <StatsCard {...args} />
    </div>
  ),
};
