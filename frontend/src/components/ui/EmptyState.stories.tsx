import type { Meta, StoryObj } from '@storybook/react';
import { BarChart3, TrendingUp } from 'lucide-react';
import { Button } from './Button';
import { EmptyState, NoChartsAvailable, NoProgressData } from './EmptyState';

const meta = {
  title: 'HPP/EmptyState',
  component: EmptyState,
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {
  args: {
    icon: TrendingUp,
    title: 'No progress data yet',
    description: 'Start tracking your health journey to see charts and insights here.',
    action: <Button>Start tracking</Button>,
  },
};

export const Error: Story = {
  args: {
    icon: BarChart3,
    title: 'Charts not available',
    description: 'Unable to load progress charts at the moment. Please try again later.',
    state: 'error',
    action: <Button variant="secondary">Retry</Button>,
  },
};

export const LoadingStatus: Story = {
  args: {
    title: 'Preparing your plan',
    description: 'We are loading the latest governed review state.',
    state: 'loading',
  },
};

export const ProgressPreset: Story = {
  render: () => <NoProgressData onStartTracking={() => undefined} />,
};

export const ChartsPreset: Story = {
  render: () => <NoChartsAvailable onRetry={() => undefined} />,
};
