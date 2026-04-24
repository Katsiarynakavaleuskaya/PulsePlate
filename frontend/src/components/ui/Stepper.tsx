import type { HTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

export interface StepperItem {
  id: string;
  label: string;
  description?: string;
}

export interface StepperProps extends HTMLAttributes<HTMLElement> {
  ariaLabel: string;
  currentStep: number;
  progressLabel: ReactNode;
  steps: StepperItem[];
}

function resolveStepState(index: number, currentStep: number): 'completed' | 'current' | 'upcoming' {
  if (index < currentStep) {
    return 'completed';
  }
  if (index === currentStep) {
    return 'current';
  }
  return 'upcoming';
}

export function Stepper({
  ariaLabel,
  className = '',
  currentStep,
  progressLabel,
  steps,
  ...props
}: StepperProps): JSX.Element | null {
  if (steps.length === 0) {
    return null;
  }

  const safeCurrentStep = Math.min(Math.max(currentStep, 0), Math.max(steps.length - 1, 0));
  const currentLabel = steps[safeCurrentStep]?.label ?? '';

  return (
    <nav
      aria-label={ariaLabel}
      className={clsx('rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4', className)}
      {...props}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
        {progressLabel}
      </p>
      <p className="mt-2 text-sm font-medium text-[var(--color-text)]">{currentLabel}</p>
      <ol className="mt-4 grid gap-3 sm:grid-cols-[repeat(auto-fit,minmax(0,1fr))]">
        {steps.map((step, index) => {
          const state = resolveStepState(index, safeCurrentStep);
          const isCurrent = state === 'current';
          const isCompleted = state === 'completed';

          return (
            <li
              key={step.id}
              aria-current={isCurrent ? 'step' : undefined}
              className={clsx(
                'rounded-xl border px-4 py-3',
                isCurrent
                  ? 'border-[var(--color-primary)] bg-[rgba(51,159,255,0.08)]'
                  : isCompleted
                    ? 'border-[rgba(32,201,151,0.28)] bg-[rgba(32,201,151,0.06)]'
                    : 'border-[var(--color-border)] bg-[var(--color-bg)]'
              )}
            >
              <div className="flex items-start gap-3">
                <span
                  className={clsx(
                    'inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                    isCurrent
                      ? 'bg-[var(--color-primary)] text-[var(--color-primary-foreground)]'
                      : isCompleted
                        ? 'bg-[var(--color-success)] text-[var(--color-primary-foreground)]'
                        : 'bg-[var(--color-surface-muted)] text-[var(--color-text)]'
                  )}
                >
                  {index + 1}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-[var(--color-text)]">{step.label}</span>
                  {step.description ? (
                    <span className="mt-1 block text-xs text-[var(--color-text-muted)]">{step.description}</span>
                  ) : null}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export default Stepper;
