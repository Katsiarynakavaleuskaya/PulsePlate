import type { HTMLAttributes, ReactNode } from 'react';
import clsx from 'clsx';

export interface HeroProps extends HTMLAttributes<HTMLElement> {
  eyebrow?: string;
  title: string;
  description?: string;
  chips?: ReactNode;
  actions?: ReactNode;
  aside?: ReactNode;
}

export function Hero({
  actions,
  aside,
  chips,
  className = '',
  description,
  eyebrow,
  title,
  ...props
}: HeroProps): JSX.Element {
  return (
    <section
      className={clsx(
        'rounded-[1.75rem] border border-white/12 bg-white/[0.08] p-6 shadow-[0_30px_60px_rgba(15,23,42,0.28)] sm:p-8',
        className
      )}
      {...props}
    >
      <div className={clsx('grid gap-6', aside ? 'lg:grid-cols-[minmax(0,1fr)_minmax(14rem,18rem)] lg:items-start' : '')}>
        <div>
          {eyebrow ? (
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-white/52">{eyebrow}</p>
          ) : null}
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.06em] text-white sm:text-5xl">{title}</h1>
          {description ? (
            <p className="mt-3 max-w-2xl text-sm leading-7 text-white/62 sm:text-base">{description}</p>
          ) : null}
          {chips ? <div className="mt-6 flex flex-wrap gap-3">{chips}</div> : null}
          {actions ? <div className="mt-6 flex flex-wrap gap-3">{actions}</div> : null}
        </div>
        {aside ? <div>{aside}</div> : null}
      </div>
    </section>
  );
}

export default Hero;
