import type { HTMLAttributes } from 'react';
import clsx from 'clsx';

type BadgeSize = 'sm' | 'md' | 'lg';
type BadgeTone = 'default' | 'premium' | 'success' | 'warning';
type BadgeVariant = 'solid' | 'outline' | 'subtle';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  size?: BadgeSize;
  tone?: BadgeTone;
  variant?: BadgeVariant;
}

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

const toneVariantClasses: Record<BadgeTone, Record<BadgeVariant, string>> = {
  default: {
    solid:
      'bg-[var(--color-primary)] text-[var(--color-primary-foreground)] ring-1 ring-[var(--color-primary)]/20',
    outline:
      'border border-[var(--color-border)] bg-transparent text-[var(--color-text)] ring-1 ring-[var(--color-border)]/35',
    subtle:
      'border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)] ring-1 ring-[var(--color-border)]/20',
  },
  premium: {
    solid:
      'bg-gradient-to-r from-[var(--pp-gold)] to-[var(--pp-navy)] text-[var(--color-primary-foreground)] ring-1 ring-[var(--pp-navy)]/25',
    outline:
      'border border-[var(--pp-gold)] bg-transparent text-[var(--color-text)] ring-1 ring-[var(--pp-gold)]/35',
    subtle:
      'border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)] ring-1 ring-[var(--pp-gold)]/20',
  },
  success: {
    solid:
      'bg-[rgba(32,201,151,0.16)] text-[var(--color-success)] ring-1 ring-[rgba(32,201,151,0.24)]',
    outline:
      'border border-[rgba(32,201,151,0.32)] bg-transparent text-[var(--color-success)] ring-1 ring-[rgba(32,201,151,0.16)]',
    subtle:
      'border border-[rgba(32,201,151,0.2)] bg-[rgba(32,201,151,0.08)] text-[var(--color-success)] ring-1 ring-[rgba(32,201,151,0.12)]',
  },
  warning: {
    solid:
      'bg-[var(--color-warning)] text-[var(--color-primary-foreground)] ring-1 ring-[var(--color-warning)]/25',
    outline:
      'border border-[var(--color-warning)] bg-transparent text-[var(--color-warning)] ring-1 ring-[var(--color-warning)]/20',
    subtle:
      'border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/10 text-[var(--color-warning)] ring-1 ring-[var(--color-warning)]/15',
  },
};

export function Badge({
  children,
  className = '',
  size = 'md',
  tone = 'default',
  variant = 'solid',
  ...props
}: BadgeProps): JSX.Element {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full font-medium',
        sizeClasses[size],
        toneVariantClasses[tone][variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export default Badge;
