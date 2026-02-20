import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import SegmentedControl from './SegmentedControl';

type RangeOption = 'WEEK' | 'MONTH' | 'QUARTER';

function SegmentedControlDemo(): JSX.Element {
  const [value, setValue] = useState<RangeOption>('MONTH');

  return (
    <div className="space-y-3">
      <SegmentedControl
        options={['WEEK', 'MONTH', 'QUARTER'] as const}
        value={value}
        onChange={setValue}
        ariaLabel="Progress range"
      />
      <p className="text-sm text-[var(--color-text-muted)]">Current window: {value}</p>
    </div>
  );
}

const meta: Meta<typeof SegmentedControlDemo> = {
  title: 'HPP/SegmentedControl',
  component: SegmentedControlDemo,
};

export default meta;
type Story = StoryObj<typeof SegmentedControlDemo>;

export const Default: Story = {};
