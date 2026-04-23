import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';
import { Alert } from './Alert';

const meta: Meta<typeof Alert> = {
  title: 'HPP/Alert',
  component: Alert,
};

export default meta;
type Story = StoryObj<typeof Alert>;

export const Info: Story = {
  args: {
    children: 'Your weekly plan is ready for review.',
    title: 'Planning update',
    tone: 'info',
  },
};

export const Success: Story = {
  args: {
    children: 'The latest primitive additions are now visible in Storybook-first review.',
    title: 'Review lane synced',
    tone: 'success',
  },
};

export const WarningWithAction: Story = {
  args: {
    action: <Button size="sm" variant="secondary">Review state</Button>,
    children: 'One required meal preference is still missing from the setup flow.',
    title: 'Needs attention',
    tone: 'warning',
  },
};

export const ErrorLongCopy: Story = {
  args: {
    children:
      'The plan could not be saved because the current session lost permission to update the draft. Refresh the page and retry the action from the same planning lane.',
    title: 'Save failed',
    tone: 'error',
  },
};
