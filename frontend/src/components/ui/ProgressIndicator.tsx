import type { HTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

export type ProgressIndicatorVariant = 'compact' | 'emphasized';
export type ProgressIndicatorState = 'live' | 'static' | 'complete' | 'warning';

export interface ProgressIndicatorProps extends HTMLAttributes<HTMLElement> {
  label: string;
  description?: string;
  timestampLabel?: string;
  timestampAriaLabel?: string;
  action?: ReactNode;
  state?: ProgressIndicatorState;
  variant?: ProgressIndicatorVariant;
}

const stateDotClasses: Record<ProgressIndicatorState, string> = {
  live: 'bg-[var(--color-success)] animate-pulse',
  static: 'bg-[var(--color-warning)]',
  complete: 'bg-[var(--color-primary)]',
  warning: 'bg-[var(--color-error)]',
};

export function ProgressIndicator({
  action,
  className = '',
  description,
  label,
  state = 'static',
  timestampAriaLabel = 'Progress timestamp',
  timestampLabel,
  variant = 'compact',
  ...props
}: ProgressIndicatorProps): JSX.Element {
  return (
    <section
      className={clsx(
        'space-y-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]',
        variant === 'emphasized' ? 'p-5 shadow-sm' : 'p-4',
        className
      )}
      data-state={state}
      data-variant={variant}
      {...props}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className={clsx('h-2.5 w-2.5 rounded-full', stateDotClasses[state])}
          />
          <p className="text-sm font-medium text-[var(--color-text)]">{label}</p>
        </div>
        {timestampLabel ? (
          <p className="text-xs text-[var(--color-text-muted)]" aria-label={timestampAriaLabel}>
            {timestampLabel}
          </p>
        ) : null}
      </div>
      {description ? (
        <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
      ) : null}
      {action ? <div>{action}</div> : null}
    </section>
  );
}

export default ProgressIndicator;
