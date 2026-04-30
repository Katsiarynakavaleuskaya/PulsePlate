import type { Meta, StoryObj } from '@storybook/react';
import { CardSkeleton, ChartSkeleton, ProgressPageSkeleton, Skeleton } from './Skeleton';

const meta = {
  title: 'HPP/Skeleton',
  component: Skeleton,
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Decorative: Story = {
  args: {
    className: 'h-10 w-64',
  },
};

export const LabeledStatus: Story = {
  args: {
    ariaLabel: 'Loading weekly progress',
    className: 'h-10 w-64',
  },
};

export const Card: Story = {
  render: () => <CardSkeleton />,
};

export const Chart: Story = {
  render: () => <ChartSkeleton />,
};

export const ProgressPage: Story = {
  render: () => <ProgressPageSkeleton />,
  parameters: {
    layout: 'fullscreen',
  },
};
