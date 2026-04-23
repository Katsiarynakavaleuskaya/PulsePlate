import type { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { RadioGroup, RadioGroupOption } from './RadioGroup';

function RadioGroupDemo({ error = false }: { error?: boolean }) {
  const [value, setValue] = useState('calm');

  return (
    <div className="w-[360px]">
      <RadioGroup error={error ? 'Choose one coaching tone for your plan.' : undefined} legend="Coaching tone">
        <RadioGroupOption
          checked={value === 'calm'}
          description="Minimal, confident guidance"
          label="Calm"
          name="coaching-tone"
          value="calm"
          onChange={(event) => setValue(event.target.value)}
        />
        <RadioGroupOption
          checked={value === 'motivated'}
          description="Slightly more energetic coaching"
          label="Motivated"
          name="coaching-tone"
          value="motivated"
          onChange={(event) => setValue(event.target.value)}
        />
        <RadioGroupOption
          description="Fewer prompts, more self-directed planning"
          disabled
          label="Quiet"
          name="coaching-tone"
          value="quiet"
        />
      </RadioGroup>
    </div>
  );
}

const meta: Meta<typeof RadioGroupDemo> = {
  title: 'HPP/RadioGroup',
  component: RadioGroupDemo,
};

export default meta;
type Story = StoryObj<typeof RadioGroupDemo>;

export const Default: Story = {};

export const ErrorState: Story = {
  args: { error: true },
};
