import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { Checkbox } from './Checkbox';

function CheckboxDemo({
  disabled = false,
  error = false,
}: {
  disabled?: boolean;
  error?: boolean;
}) {
  const [checked, setChecked] = useState(true);

  return (
    <div className="w-[360px] space-y-2">
      <label className="flex items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-3">
        <Checkbox
          checked={checked}
          disabled={disabled}
          invalid={error}
          onChange={(event) => setChecked(event.target.checked)}
        />
        <span className="space-y-1">
          <span className="block text-sm font-medium text-[var(--color-text)]">Email me the weekly planning summary</span>
          <span className="block text-sm text-[var(--color-text-muted)]">
            Keep weekly planning reminders supportive and low-noise.
          </span>
        </span>
      </label>
      {error ? <p className="text-sm text-[var(--color-error)]">Consent is required before enabling reminders.</p> : null}
    </div>
  );
}

const meta: Meta<typeof CheckboxDemo> = {
  title: 'HPP/Checkbox',
  component: CheckboxDemo,
};

export default meta;
type Story = StoryObj<typeof CheckboxDemo>;

export const Default: Story = {};

export const Disabled: Story = {
  args: { disabled: true },
};

export const ErrorState: Story = {
  args: { error: true },
};
