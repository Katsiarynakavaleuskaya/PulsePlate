import type { Meta, StoryObj } from '@storybook/react';
import { Badge } from './Badge';

const meta: Meta<typeof Badge> = {
  title: 'HPP/Badge',
  component: Badge,
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Premium: Story = {
  args: {
    children: 'VIP',
    tone: 'premium',
  },
};

export const Outline: Story = {
  args: {
    children: 'Review',
    tone: 'warning',
    variant: 'outline',
  },
};

export const SubtleSuccess: Story = {
  args: {
    children: 'Synced',
    tone: 'success',
    variant: 'subtle',
  },
};
