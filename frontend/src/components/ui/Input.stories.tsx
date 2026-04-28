import type { Meta, StoryObj } from '@storybook/react';
import { Input } from './Input';

const meta = {
  title: 'HPP/Input',
  component: Input,
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TextDefault: Story = {
  args: {
    'aria-label': 'Text input',
    placeholder: 'Placeholder',
    type: 'text',
  },
};

export const TextFilled: Story = {
  args: {
    'aria-label': 'Filled input',
    readOnly: true,
    value: 'Value',
    type: 'text',
  },
};

export const TextError: Story = {
  args: {
    'aria-label': 'Error input',
    type: 'text',
    invalid: true,
    placeholder: 'Placeholder',
  },
};

export const TextDisabled: Story = {
  args: {
    'aria-label': 'Disabled input',
    type: 'text',
    disabled: true,
    value: 'Disabled',
  },
};

export const NumberDefault: Story = {
  args: {
    'aria-label': 'Calories',
    type: 'number',
    value: 1800,
    readOnly: true,
  },
};

export const SearchDefault: Story = {
  args: {
    'aria-label': 'Search foods',
    type: 'search',
    placeholder: 'Search foods',
  },
};

export const SecretDefault: Story = {
  args: {
    'aria-label': 'API key',
    type: 'password',
    value: 'secret-key',
    readOnly: true,
  },
};

export const Loading: Story = {
  args: {
    'aria-label': 'Async validation',
    loading: true,
    placeholder: 'Validating…',
  },
};

export const Sizes: Story = {
  render: () => (
    <div className="flex w-[320px] flex-col gap-3">
      <Input aria-label="Small input" placeholder="Small" size="sm" />
      <Input aria-label="Medium input" placeholder="Medium" size="md" />
      <Input aria-label="Large input" placeholder="Large" size="lg" />
    </div>
  ),
};
