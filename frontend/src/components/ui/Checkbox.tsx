import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  invalid?: boolean;
}

function hasInvalidState(value: CheckboxProps['aria-invalid'], invalid: boolean | undefined) {
  return invalid || value === true || value === 'true';
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className = '', invalid, 'aria-invalid': ariaInvalid, ...props },
  ref
) {
  const isInvalid = hasInvalidState(ariaInvalid, invalid);

  return (
    <input
      {...props}
      ref={ref}
      aria-invalid={isInvalid || undefined}
      className={[
        'h-4 w-4 rounded border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-primary)]',
        'focus:ring-[var(--color-primary)]',
        isInvalid ? 'border-[var(--color-error)]' : '',
        className,
      ]
        .join(' ')
        .trim()}
      type="checkbox"
    />
  );
});

Checkbox.displayName = 'Checkbox';

export default Checkbox;
