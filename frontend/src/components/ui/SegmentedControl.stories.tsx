import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import SegmentedControl from './SegmentedControl';

type RangeOption = 'WEEK' | 'MONTH' | 'QUARTER';
type RangeOptionExtended = RangeOption | 'YEAR';

interface SegmentedControlDemoProps {
  options: readonly RangeOptionExtended[];
  initialValue: RangeOptionExtended;
  ariaLabel: string;
}

function SegmentedControlDemo({
  options,
  initialValue,
  ariaLabel,
}: SegmentedControlDemoProps): JSX.Element {
  const [value, setValue] = useState<RangeOptionExtended>(initialValue);

  return (
    <div className="space-y-3">
      <SegmentedControl
        options={options}
        value={value}
        onChange={setValue}
        ariaLabel={ariaLabel}
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

export const Default: Story = {
  args: {
    options: ['WEEK', 'MONTH', 'QUARTER'],
    initialValue: 'MONTH',
    ariaLabel: 'Progress range',
  },
};

export const TwoOptions: Story = {
  args: {
    options: ['WEEK', 'MONTH'],
    initialValue: 'WEEK',
    ariaLabel: 'Short range',
  },
};

export const FourOptions: Story = {
  args: {
    options: ['WEEK', 'MONTH', 'QUARTER', 'YEAR'],
    initialValue: 'QUARTER',
    ariaLabel: 'Extended range',
  },
};
