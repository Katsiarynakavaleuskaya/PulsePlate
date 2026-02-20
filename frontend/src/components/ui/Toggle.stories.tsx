import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { Toggle } from './Toggle';

function ToggleDemo() {
  const [enabled, setEnabled] = useState(false);

  return (
    <div className="space-y-3">
      <Toggle label="Enable live progress signal" checked={enabled} onChange={setEnabled} />
      <p className="text-sm text-[var(--color-text-muted)]">State: {enabled ? 'On' : 'Off'}</p>
    </div>
  );
}

const meta: Meta<typeof ToggleDemo> = {
  title: 'HPP/Toggle',
  component: ToggleDemo,
};

export default meta;
type Story = StoryObj<typeof ToggleDemo>;

export const Default: Story = {};
