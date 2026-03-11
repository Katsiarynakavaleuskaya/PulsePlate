import type { Meta, StoryObj } from '@storybook/react';
import { BrandIdentityPanel } from './BrandPanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof BrandIdentityPanel> = {
  title: 'PulsePlate/Patterns/BrandIdentityPanel',
  component: BrandIdentityPanel,
  render: () => (
    <DesignSystemCanvas>
      <BrandIdentityPanel />
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof BrandIdentityPanel>;

export const Default: Story = {};
