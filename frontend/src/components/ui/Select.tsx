import { forwardRef } from 'react';
import type { SelectHTMLAttributes } from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options?: SelectOption[];
  invalid?: boolean;
  placeholder?: string;
}

function hasInvalidState(value: SelectProps['aria-invalid'], invalid: boolean | undefined) {
  return invalid || value === true || value === 'true';
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className = '', options = [], invalid, placeholder, children, 'aria-invalid': ariaInvalid, ...props },
  ref
) {
  const isInvalid = hasInvalidState(ariaInvalid, invalid);

  return (
    <div className="relative">
      <select
        ref={ref}
        aria-invalid={isInvalid || undefined}
        className={[
          'w-full appearance-none rounded-lg border bg-[var(--color-bg)] px-3 py-2 pr-10',
          'text-[var(--color-text)]',
          'focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-1',
          'disabled:cursor-not-allowed disabled:opacity-60',
          isInvalid ? 'border-[var(--color-error)]' : 'border-[var(--color-border)]',
          className,
        ]
          .join(' ')
          .trim()}
        {...props}
      >
        {placeholder ? <option value="">{placeholder}</option> : null}
        {options.map((option) => (
          <option key={option.value} disabled={option.disabled} value={option.value}>
            {option.label}
          </option>
        ))}
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]"
      />
    </div>
  );
});

Select.displayName = 'Select';

export default Select;
