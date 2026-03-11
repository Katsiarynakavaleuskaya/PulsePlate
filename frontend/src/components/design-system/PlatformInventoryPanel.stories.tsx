import type { Meta, StoryObj } from '@storybook/react';
import { PlatformInventoryPanel } from './ExperiencePanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof PlatformInventoryPanel> = {
  title: 'PulsePlate/Patterns/PlatformInventoryPanel',
  component: PlatformInventoryPanel,
  render: () => (
    <DesignSystemCanvas>
      <PlatformInventoryPanel />
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof PlatformInventoryPanel>;

export const Default: Story = {};
