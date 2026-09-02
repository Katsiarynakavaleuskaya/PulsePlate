import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { FormField } from './FormField';
import { Select } from './Select';

const options = [
  { value: 'breakfast', label: 'Breakfast' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'dinner', label: 'Dinner' },
  { value: 'snack', label: 'Snack' },
];

function SelectDemo({
  disabled = false,
  invalid = false,
  longOptions = false,
}: {
  disabled?: boolean;
  invalid?: boolean;
  longOptions?: boolean;
}) {
  const [value, setValue] = useState('lunch');

  return (
    <div className="w-[320px]">
      <FormField
        error={
          invalid
            ? { type: 'validate', message: 'Choose the planning slot for this meal.' }
            : undefined
        }
        label="Primary meal slot"
        name="meal-slot"
      >
        <Select
          disabled={disabled}
          invalid={invalid}
          options={
            longOptions
              ? options.map((option) => ({
                  ...option,
                  label: `${option.label} with a longer planning description for review`,
                }))
              : options
          }
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
      </FormField>
    </div>
  );
}

const meta: Meta<typeof SelectDemo> = {
  title: 'HPP/Select',
  component: SelectDemo,
};

export default meta;
type Story = StoryObj<typeof SelectDemo>;

export const Default: Story = {};

export const ErrorState: Story = {
  args: { invalid: true },
};

export const Disabled: Story = {
  args: { disabled: true },
};

export const LongOptions: Story = {
  args: { longOptions: true },
};
