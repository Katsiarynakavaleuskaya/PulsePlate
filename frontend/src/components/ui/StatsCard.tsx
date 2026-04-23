import type { HTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

type StatsCardTone = 'default' | 'inverse';
type StatsCardAlign = 'left' | 'center';

export interface StatsCardProps extends HTMLAttributes<HTMLDivElement> {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  unit?: ReactNode;
  tone?: StatsCardTone;
  align?: StatsCardAlign;
}

const toneClasses: Record<StatsCardTone, string> = {
  default: 'border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)]',
  inverse: 'border-white/12 bg-white/[0.08] text-white shadow-none',
};

export function StatsCard({
  align = 'left',
  className = '',
  detail,
  label,
  tone = 'default',
  unit,
  value,
  ...props
}: StatsCardProps): JSX.Element {
  const isInverse = tone === 'inverse';

  return (
    <div
      className={clsx(
        'rounded-xl border p-4 transition-shadow hover:shadow-sm',
        toneClasses[tone],
        align === 'center' ? 'text-center' : '',
        className
      )}
      {...props}
    >
      <div className={clsx('text-sm mb-1', isInverse ? 'text-white/48' : 'text-[var(--color-text-muted)]')}>
        {label}
      </div>
      <div
        className={clsx(
          'font-bold',
          isInverse ? 'text-2xl tracking-[-0.04em] text-white' : 'text-xl text-[var(--color-text)]'
        )}
      >
        {value}
      </div>
      {unit !== null && unit !== undefined ? (
        <div className={clsx('text-xs mt-1', isInverse ? 'text-white/56' : 'text-[var(--color-text-muted)]')}>
          {unit}
        </div>
      ) : null}
      {detail !== null && detail !== undefined ? (
        <div className={clsx('text-xs mt-1', isInverse ? 'text-white/56' : 'text-[var(--color-text-muted)]')}>
          {detail}
        </div>
      ) : null}
    </div>
  );
}

export default StatsCard;
