import type { Meta, StoryObj } from '@storybook/react';
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuItems,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './DropdownMenu';

const meta: Meta<typeof DropdownMenu> = {
  title: 'HPP/DropdownMenu',
  component: DropdownMenu,
  decorators: [
    (Story) => (
      <div className="min-h-[220px] p-8">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof DropdownMenu>;

export const Default: Story = {
  render: () => (
    <DropdownMenu>
      <DropdownMenuTrigger>More actions</DropdownMenuTrigger>
      <DropdownMenuItems>
        <DropdownMenuItem>
          <span className="block font-medium">Duplicate template</span>
          <span className="block text-xs text-[var(--color-text-muted)]">Reuse this plan structure</span>
        </DropdownMenuItem>
        <DropdownMenuItem>Share with partner</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem destructive>Remove template</DropdownMenuItem>
      </DropdownMenuItems>
    </DropdownMenu>
  ),
};

export const DisabledItem: Story = {
  render: () => (
    <DropdownMenu>
      <DropdownMenuTrigger>Plan actions</DropdownMenuTrigger>
      <DropdownMenuItems>
        <DropdownMenuItem disabled>Publish to team library</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem>Archive draft</DropdownMenuItem>
      </DropdownMenuItems>
    </DropdownMenu>
  ),
};
