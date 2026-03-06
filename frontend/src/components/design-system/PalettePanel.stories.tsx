import type { Meta, StoryObj } from '@storybook/react';
import { PalettePanel } from './TokenPanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof PalettePanel> = {
  title: 'PulsePlate/Tokens/PalettePanel',
  component: PalettePanel,
  render: () => (
    <DesignSystemCanvas>
      <PalettePanel />
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof PalettePanel>;

export const Default: Story = {};
