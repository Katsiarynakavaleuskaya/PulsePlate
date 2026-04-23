import { forwardRef } from 'react';
import type { TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

function hasInvalidState(value: TextareaProps['aria-invalid'], invalid: boolean | undefined) {
  return invalid || value === true || value === 'true';
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className = '', invalid, rows = 4, 'aria-invalid': ariaInvalid, ...props },
  ref
) {
  const isInvalid = hasInvalidState(ariaInvalid, invalid);

  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={isInvalid || undefined}
      className={[
        'w-full rounded-lg border bg-[var(--color-bg)] px-3 py-3',
        'text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]',
        'focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-1',
        'disabled:cursor-not-allowed disabled:opacity-60',
        'min-h-[120px] resize-y',
        isInvalid ? 'border-[var(--color-error)]' : 'border-[var(--color-border)]',
        className,
      ]
        .join(' ')
        .trim()}
      {...props}
    />
  );
});

Textarea.displayName = 'Textarea';

export default Textarea;
