import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { Toggle } from './Toggle';

interface ToggleDemoProps {
  label: string;
  defaultChecked: boolean;
  disabled?: boolean;
}

function ToggleDemo({ label, defaultChecked, disabled = false }: ToggleDemoProps): JSX.Element {
  const [enabled, setEnabled] = useState(defaultChecked);

  return (
    <div className="space-y-3">
      <Toggle label={label} checked={enabled} onChange={setEnabled} disabled={disabled} />
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

export const Default: Story = {
  args: {
    label: 'Enable live progress signal',
    defaultChecked: false,
    disabled: false,
  },
};

export const Enabled: Story = {
  args: {
    label: 'Enable live progress signal',
    defaultChecked: true,
    disabled: false,
  },
};

export const DisabledOff: Story = {
  args: {
    label: 'Enable live progress signal',
    defaultChecked: false,
    disabled: true,
  },
};

export const DisabledOn: Story = {
  args: {
    label: 'Enable live progress signal',
    defaultChecked: true,
    disabled: true,
  },
};
