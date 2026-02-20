import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';

type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className = '', ...props },
  ref
) {
  return (
    <input
      ref={ref}
      className={[
        'w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2',
        'text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]',
        'focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-1',
        className,
      ]
        .join(' ')
        .trim()}
      {...props}
    />
  );
});

Input.displayName = 'Input';

export default Input;
