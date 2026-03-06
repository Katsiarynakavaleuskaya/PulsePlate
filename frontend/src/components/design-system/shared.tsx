import type { PropsWithChildren } from 'react';
import { Card, CardContent } from '../ui';

interface PanelShellProps extends PropsWithChildren {
  title: string;
  subtitle?: string;
  className?: string;
}

export function DesignSystemCanvas({ children }: PropsWithChildren) {
  return (
    <div className="bg-design-system-canvas min-h-screen p-6 sm:p-8">
      <div className="mx-auto max-w-7xl">{children}</div>
    </div>
  );
}

export function OverviewHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="mb-5">
      <p className="text-[11px] font-medium uppercase tracking-[0.28em] text-white/35">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-white">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-white/62">{description}</p>
    </div>
  );
}

export function PanelShell({
  title,
  subtitle,
  className = '',
  children,
}: PanelShellProps) {
  return (
    <Card
      className={[
        'h-full border-white/8 bg-white/[0.05] shadow-[0_20px_60px_rgba(0,0,0,0.24)]',
        className,
      ].join(' ').trim()}
    >
      <CardContent className="h-full p-5">
        <div className="mb-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-white/35">{title}</p>
          {subtitle ? <p className="mt-2 text-sm text-white/60">{subtitle}</p> : null}
        </div>
        {children}
      </CardContent>
    </Card>
  );
}
