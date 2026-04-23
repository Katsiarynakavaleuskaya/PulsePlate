import { useId } from 'react';
import type { InputHTMLAttributes, PropsWithChildren, ReactElement, ReactNode } from 'react';
import { hasInvalidState } from './fieldState';

interface RadioGroupProps extends PropsWithChildren {
  legend: ReactNode;
  error?: string;
  orientation?: 'vertical' | 'horizontal';
}

interface RadioGroupOptionProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: ReactNode;
  description?: ReactNode;
  invalid?: boolean;
}

export function RadioGroup({
  children,
  error,
  legend,
  orientation = 'vertical',
}: RadioGroupProps): ReactElement {
  const generatedId = useId();
  const errorId = error ? `radio-group-${generatedId}-error` : undefined;

  return (
    <fieldset aria-describedby={errorId} className="space-y-3">
      <legend className="text-sm font-medium text-[var(--color-text)]">{legend}</legend>
      <div className={orientation === 'horizontal' ? 'grid gap-3 md:grid-cols-2' : 'space-y-3'}>
        {children}
      </div>
      {error ? (
        <p className="text-sm text-[var(--color-error)]" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}

export function RadioGroupOption({
  label,
  description,
  invalid = false,
  className = '',
  ...props
}: RadioGroupOptionProps): ReactElement {
  const isInvalid = hasInvalidState(props['aria-invalid'], invalid);

  return (
    <label
      className={[
        'flex items-start gap-3 rounded-lg border px-3 py-3',
        props.disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer',
        invalid ? 'border-[var(--color-error)]' : 'border-[var(--color-border)]',
        'bg-[var(--color-bg)]',
        className,
      ]
        .join(' ')
        .trim()}
    >
      <input
        {...props}
        aria-invalid={isInvalid || undefined}
        className="mt-0.5 h-4 w-4 border-[var(--color-border)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
        type="radio"
      />
      <span className="min-w-0 space-y-1">
        <span className="block text-sm font-medium text-[var(--color-text)]">{label}</span>
        {description ? <span className="block text-sm text-[var(--color-text-muted)]">{description}</span> : null}
      </span>
    </label>
  );
}

export default RadioGroup;
