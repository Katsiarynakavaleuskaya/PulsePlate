import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import type { InputHTMLAttributes } from 'react';
import { hasInvalidState } from './fieldState';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  indeterminate?: boolean;
  invalid?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className = '', indeterminate = false, invalid, 'aria-checked': ariaChecked, 'aria-invalid': ariaInvalid, ...props },
  ref
) {
  const isInvalid = hasInvalidState(ariaInvalid, invalid);
  const inputRef = useRef<HTMLInputElement>(null);

  useImperativeHandle(ref, () => inputRef.current as HTMLInputElement);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.indeterminate = indeterminate;
    }
  }, [indeterminate]);

  return (
    <input
      {...props}
      ref={inputRef}
      aria-checked={ariaChecked ?? (indeterminate ? 'mixed' : undefined)}
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
