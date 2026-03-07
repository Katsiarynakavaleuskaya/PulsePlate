import type { Meta, StoryObj } from '@storybook/react';
import { SpacingRadiusPanel } from './TokenPanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof SpacingRadiusPanel> = {
  title: 'PulsePlate/Tokens/SpacingRadiusPanel',
  component: SpacingRadiusPanel,
  render: () => (
    <DesignSystemCanvas>
      <SpacingRadiusPanel />
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof SpacingRadiusPanel>;

export const Default: Story = {};
