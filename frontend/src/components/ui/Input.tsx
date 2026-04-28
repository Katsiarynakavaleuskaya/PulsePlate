import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';
import { hasInvalidState } from './fieldState';

export type InputSize = 'sm' | 'md' | 'lg';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  size?: InputSize;
  invalid?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
}

const sizeClasses: Record<InputSize, string> = {
  sm: 'min-h-[40px] rounded-lg px-3 py-2 text-sm',
  md: 'min-h-[44px] rounded-lg px-3 py-2 text-sm',
  lg: 'min-h-[48px] rounded-xl px-4 py-3 text-base',
};

export function inputClasses({
  size = 'md',
  invalid = false,
  fullWidth = true,
  className = '',
}: {
  size?: InputSize;
  invalid?: boolean;
  fullWidth?: boolean;
  className?: string;
}): string {
  return [
    fullWidth ? 'w-full' : '',
    'border bg-[var(--color-bg)]',
    'text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]',
    'focus:outline-none focus:ring-2 focus:ring-offset-1',
    'disabled:cursor-not-allowed disabled:opacity-60',
    invalid
      ? 'border-[var(--color-error)] focus:ring-[var(--color-error)]'
      : 'border-[var(--color-border)] focus:ring-[var(--color-primary)]',
    sizeClasses[size],
    className,
  ]
    .join(' ')
    .trim();
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    className = '',
    size = 'md',
    invalid,
    loading = false,
    fullWidth = true,
    disabled,
    'aria-invalid': ariaInvalid,
    ...props
  },
  ref
) {
  const isInvalid = hasInvalidState(ariaInvalid, invalid);
  const isDisabled = Boolean(disabled) || loading;

  return (
    <input
      ref={ref}
      {...props}
      aria-busy={loading ? true : undefined}
      aria-invalid={isInvalid || undefined}
      className={inputClasses({
        size,
        invalid: isInvalid,
        fullWidth,
        className,
      })}
      disabled={isDisabled}
    />
  );
});

Input.displayName = 'Input';

export default Input;
