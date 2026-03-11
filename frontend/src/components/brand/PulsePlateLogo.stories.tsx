import type { Meta, StoryObj } from '@storybook/react';
import { DesignSystemCanvas } from '../design-system';
import { PulsePlateLogo } from './PulsePlateLogo';

const meta: Meta<typeof PulsePlateLogo> = {
  title: 'PulsePlate/Brand/PulsePlateLogo',
  component: PulsePlateLogo,
  render: (args) => (
    <DesignSystemCanvas>
      <div
        className={[
          'flex min-h-[280px] items-center justify-center rounded-[28px] p-8',
          args.tone === 'light'
            ? 'border border-slate-200 bg-white'
            : 'border border-white/10 bg-white/[0.04]',
        ].join(' ')}
      >
        <PulsePlateLogo {...args} />
      </div>
    </DesignSystemCanvas>
  ),
};

export default meta;
type Story = StoryObj<typeof PulsePlateLogo>;

export const Mark: Story = {
  args: {
    variant: 'mark',
  },
};

export const LockupDark: Story = {
  args: {
    variant: 'lockup',
    tone: 'dark',
  },
};

export const LockupLight: Story = {
  args: {
    variant: 'lockup',
    tone: 'light',
  },
};

export const Compact: Story = {
  args: {
    variant: 'compact',
  },
};
