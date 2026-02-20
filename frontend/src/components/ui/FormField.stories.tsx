import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { FormField } from './FormField';

function FormFieldDemo(): JSX.Element {
  const [value, setValue] = useState('');

  return (
    <div className="w-[320px] space-y-4">
      <FormField label="Weight (kg)" name="weight_kg" required>
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-[var(--color-text)]"
          placeholder="e.g. 72.5"
        />
      </FormField>
    </div>
  );
}

const meta: Meta<typeof FormFieldDemo> = {
  title: 'HPP/FormField',
  component: FormFieldDemo,
};

export default meta;
type Story = StoryObj<typeof FormFieldDemo>;

export const Default: Story = {};
