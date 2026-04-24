import type { Meta, StoryObj } from '@storybook/react';
import { Hero } from './Hero';

const meta: Meta<typeof Hero> = {
  title: 'HPP/Hero',
  component: Hero,
};

export default meta;
type Story = StoryObj<typeof Hero>;

export const HomeShell: Story = {
  args: {
    chips: (
      <>
        <span className="rounded-full bg-white/[0.08] px-4 py-2 text-xs font-semibold text-white/88">
          Session Connected
        </span>
        <span className="rounded-full bg-white/[0.08] px-4 py-2 text-xs font-semibold text-white/88">
          Premium Active
        </span>
      </>
    ),
    description: 'Quick actions, premium guidance, and one AI surface that stays grounded in your current session.',
    eyebrow: 'Calm control panel',
    title: 'PulsePlate Home',
  },
  render: (args) => (
    <div className="bg-[var(--pp-navy)] p-6">
      <Hero {...args} />
    </div>
  ),
};
