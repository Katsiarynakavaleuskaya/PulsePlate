import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';
import { Tooltip } from './Tooltip';

const meta: Meta<typeof Tooltip> = {
  title: 'HPP/Tooltip',
  component: Tooltip,
  decorators: [
    (Story) => (
      <div className="flex min-h-[180px] items-center justify-center p-8">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const TopPlacement: Story = {
  args: {
    children: <Button size="sm" variant="ghost">Why this matters</Button>,
    content: 'Tooltips stay supplementary and never replace required guidance.',
    side: 'top',
  },
};

export const BottomPlacement: Story = {
  args: {
    children: <Button size="sm" variant="ghost">Focus hint</Button>,
    content: 'This helper also appears on keyboard focus for accessibility.',
    side: 'bottom',
  },
};
