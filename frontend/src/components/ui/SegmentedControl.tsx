import type { JSX } from 'react';

interface SegmentedControlProps<T extends string> {
  options: readonly T[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
}

export default function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
}: SegmentedControlProps<T>): JSX.Element {
  return (
    <div
      className="inline-flex items-center rounded-full border p-1"
      style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface-muted)' }}
      role="group"
      aria-label={ariaLabel}
    >
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className="min-h-[36px] rounded-full px-3 py-1 text-xs font-semibold transition-colors"
          style={{
            backgroundColor: value === option ? 'var(--color-surface)' : 'transparent',
            color: 'var(--color-text)',
          }}
          aria-pressed={value === option}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
