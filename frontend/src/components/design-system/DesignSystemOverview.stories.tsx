import type { Meta, StoryObj } from '@storybook/react';
import { DesignSystemOverview } from './DesignSystemOverview';

const meta: Meta<typeof DesignSystemOverview> = {
  title: 'PulsePlate/Patterns/DesignSystemOverview',
  component: DesignSystemOverview,
};

export default meta;
type Story = StoryObj<typeof DesignSystemOverview>;

export const Default: Story = {};
