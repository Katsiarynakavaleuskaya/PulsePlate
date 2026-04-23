import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { FormField } from './FormField';
import { Textarea } from './Textarea';

function TextareaDemo({
  disabled = false,
  invalid = false,
  filled = false,
}: {
  disabled?: boolean;
  invalid?: boolean;
  filled?: boolean;
}) {
  const [value, setValue] = useState(
    filled ? 'Plan two protein-forward dinners and keep the shopping list quiet.' : ''
  );

  return (
    <div className="w-[360px]">
      <FormField
        error={invalid ? { message: 'Add enough detail for the weekly plan to help.' } : undefined}
        label="Planning notes"
        name="planning-notes"
      >
        <Textarea
          disabled={disabled}
          invalid={invalid}
          placeholder="Capture a longer planning note"
          value={value}
          onChange={(event) => setValue(event.target.value)}
        />
      </FormField>
    </div>
  );
}

const meta: Meta<typeof TextareaDemo> = {
  title: 'HPP/Textarea',
  component: TextareaDemo,
};

export default meta;
type Story = StoryObj<typeof TextareaDemo>;

export const Default: Story = {};

export const Filled: Story = {
  args: { filled: true },
};

export const ErrorState: Story = {
  args: { invalid: true },
};

export const Disabled: Story = {
  args: { disabled: true, filled: true },
};
