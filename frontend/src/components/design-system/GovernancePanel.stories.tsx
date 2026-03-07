import type { Meta, StoryObj } from '@storybook/react';
import { GovernancePanel } from './ExperiencePanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof GovernancePanel> = {
  title: 'PulsePlate/Patterns/GovernancePanel',
  component: GovernancePanel,
  render: () => (
    <DesignSystemCanvas>
      <GovernancePanel />
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof GovernancePanel>;

export const Default: Story = {};
