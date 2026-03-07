import type { Meta, StoryObj } from '@storybook/react';
import { LogoVariantsPanel } from './BrandPanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof LogoVariantsPanel> = {
  title: 'PulsePlate/Patterns/LogoVariantsPanel',
  component: LogoVariantsPanel,
  render: () => (
    <DesignSystemCanvas>
      <LogoVariantsPanel />
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof LogoVariantsPanel>;

export const Default: Story = {};
