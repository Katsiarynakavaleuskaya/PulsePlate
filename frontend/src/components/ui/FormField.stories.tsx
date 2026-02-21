import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { FormField } from './FormField';
import type { FieldError } from 'react-hook-form';

interface FormFieldDemoProps {
  label: string;
  name: string;
  placeholder: string;
  required?: boolean;
  error?: FieldError;
}

function FormFieldDemo({
  label,
  name,
  placeholder,
  required = false,
  error,
}: FormFieldDemoProps): JSX.Element {
  const [value, setValue] = useState('');

  return (
    <div className="w-[320px] space-y-4">
      <FormField label={label} name={name} required={required} error={error}>
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-[var(--color-text)]"
          placeholder={placeholder}
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

export const Default: Story = {
  args: {
    label: 'Weight (kg)',
    name: 'weight_kg',
    placeholder: 'e.g. 72.5',
    required: false,
  },
};

export const Required: Story = {
  args: {
    label: 'Weight (kg)',
    name: 'weight_kg_required',
    placeholder: 'e.g. 72.5',
    required: true,
  },
};

export const ErrorState: Story = {
  args: {
    label: 'Weight (kg)',
    name: 'weight_kg_error',
    placeholder: 'e.g. 72.5',
    required: true,
    error: { type: 'manual', message: 'Please enter a valid positive weight.' },
  },
};
