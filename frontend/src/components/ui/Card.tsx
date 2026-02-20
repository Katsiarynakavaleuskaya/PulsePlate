import type { HTMLAttributes, PropsWithChildren } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {}

export function Card({ children, className = '', ...props }: PropsWithChildren<CardProps>) {
  return (
    <div
      className={[
        'rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]',
        className,
      ]
        .join(' ')
        .trim()}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div className={['px-6 pt-6', className].join(' ').trim()} {...props}>
      {children}
    </div>
  );
}

export function CardContent({
  children,
  className = '',
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div className={['px-6 pb-6', className].join(' ').trim()} {...props}>
      {children}
    </div>
  );
}

export default Card;
