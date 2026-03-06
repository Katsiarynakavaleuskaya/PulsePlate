import type { Meta, StoryObj } from '@storybook/react';
import { TypographyPanel } from './TokenPanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof TypographyPanel> = {
  title: 'PulsePlate/Tokens/TypographyPanel',
  component: TypographyPanel,
  render: () => (
    <DesignSystemCanvas>
      <TypographyPanel />
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof TypographyPanel>;

export const Default: Story = {};
