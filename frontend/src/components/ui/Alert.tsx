import type { ReactElement, ReactNode } from 'react';

export type AlertTone = 'info' | 'success' | 'warning' | 'error';

interface AlertProps {
  tone?: AlertTone;
  title?: string;
  action?: ReactNode;
  children: ReactNode;
}

const toneConfig: Record<AlertTone, { glyph: string; accent: string; liveRole: 'status' | 'alert' }> = {
  info: { glyph: 'i', accent: 'var(--color-info)', liveRole: 'status' },
  success: { glyph: 'ok', accent: 'var(--color-success)', liveRole: 'status' },
  warning: { glyph: '!', accent: 'var(--color-warning)', liveRole: 'alert' },
  error: { glyph: 'x', accent: 'var(--color-error)', liveRole: 'alert' },
};

export function Alert({ tone = 'info', title, action, children }: AlertProps): ReactElement {
  const config = toneConfig[tone];

  return (
    <div
      aria-live={config.liveRole === 'alert' ? 'assertive' : 'polite'}
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm"
      role={config.liveRole}
      style={{ borderLeftColor: config.accent, borderLeftWidth: '4px' }}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="mt-0.5 flex h-5 min-w-5 items-center justify-center rounded-full text-[10px] font-bold uppercase"
          style={{ backgroundColor: config.accent, color: 'var(--color-surface)' }}
        >
          {config.glyph}
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          {title ? (
            <p className="text-sm font-semibold" style={{ color: config.accent }}>
              {title}
            </p>
          ) : null}
          <div className="text-sm leading-6 text-[var(--color-text)]">{children}</div>
          {action ? <div className="pt-1">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}

export default Alert;
