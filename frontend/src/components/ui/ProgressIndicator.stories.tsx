import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';
import { ProgressIndicator } from './ProgressIndicator';

const meta: Meta<typeof ProgressIndicator> = {
  title: 'HPP/ProgressIndicator',
  component: ProgressIndicator,
};

export default meta;
type Story = StoryObj<typeof ProgressIndicator>;

export const Live: Story = {
  args: {
    action: <Button size="sm">Open progress</Button>,
    description: 'Shared progress anatomy for live and fallback states.',
    label: 'Live updates on',
    state: 'live',
    timestampLabel: '7:00 PM',
    variant: 'emphasized',
  },
};

export const StaticFallback: Story = {
  args: {
    action: <Button size="sm">Review setup</Button>,
    description: 'Fallback keeps CTA flow active when realtime is unavailable.',
    label: 'Static fallback',
    state: 'static',
  },
};
