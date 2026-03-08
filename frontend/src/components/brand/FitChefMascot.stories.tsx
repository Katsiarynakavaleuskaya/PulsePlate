import type { Meta, StoryObj } from '@storybook/react';
import { DesignSystemCanvas } from '../design-system';
import { FitChefMascot } from './FitChefMascot';

const meta: Meta<typeof FitChefMascot> = {
  title: 'PulsePlate/Brand/FitChefMascot',
  component: FitChefMascot,
  render: (args) => (
    <DesignSystemCanvas>
      <div className="grid min-h-[320px] place-items-center rounded-[28px] border border-white/10 bg-white/[0.04] p-8">
        <FitChefMascot {...args} />
      </div>
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof FitChefMascot>;

export const Static: Story = {
  args: {
    size: 'lg',
    variant: 'static',
  },
};

export const Wink: Story = {
  args: {
    size: 'lg',
    variant: 'wink',
  },
};
