import type { HTMLAttributes, PropsWithChildren } from 'react';

export const marketingButtonClasses = {
  primary: 'ppm-btn ppm-btn--primary',
  secondary: 'ppm-btn ppm-btn--secondary',
} as const;

export function MarketingSection({
  children,
  className = '',
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLElement>>) {
  return (
    <section
      className={['ppm-section', className].join(' ').trim()}
      {...props}
    >
      <div className="ppm-shell">{children}</div>
    </section>
  );
}

interface SectionHeaderProps extends HTMLAttributes<HTMLDivElement> {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: 'left' | 'center';
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  align = 'left',
  className = '',
  ...props
}: SectionHeaderProps) {
  const alignmentClass = align === 'center' ? 'ppm-header ppm-header--center' : 'ppm-header';

  return (
    <div className={[alignmentClass, className].join(' ').trim()} {...props}>
      {eyebrow ? <p className="ppm-eyebrow">{eyebrow}</p> : null}
      <h2 className="ppm-title">{title}</h2>
      {description ? <p className="ppm-description">{description}</p> : null}
    </div>
  );
}

export function MarketingCard({
  children,
  className = '',
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={['ppm-card', className].join(' ').trim()}
      {...props}
    >
      {children}
    </div>
  );
}

export function StatusPill({
  children,
  className = '',
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLSpanElement>>) {
  return (
    <span
      className={['ppm-pill', className].join(' ').trim()}
      {...props}
    >
      {children}
    </span>
  );
}
