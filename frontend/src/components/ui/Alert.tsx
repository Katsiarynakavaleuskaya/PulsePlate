import type { ReactNode } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react';

export type AlertTone = 'info' | 'success' | 'warning' | 'error';

interface AlertProps {
  tone?: AlertTone;
  title?: string;
  action?: ReactNode;
  children: ReactNode;
}

const toneConfig: Record<AlertTone, { icon: typeof Info; accent: string; liveRole: 'status' | 'alert' }> = {
  info: { icon: Info, accent: 'var(--color-info)', liveRole: 'status' },
  success: { icon: CheckCircle2, accent: 'var(--color-success)', liveRole: 'status' },
  warning: { icon: AlertTriangle, accent: 'var(--color-warning)', liveRole: 'alert' },
  error: { icon: AlertCircle, accent: 'var(--color-error)', liveRole: 'alert' },
};

export function Alert({ tone = 'info', title, action, children }: AlertProps) {
  const config = toneConfig[tone];
  const Icon = config.icon;

  return (
    <div
      aria-live={config.liveRole === 'alert' ? 'assertive' : 'polite'}
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm"
      role={config.liveRole}
      style={{ borderLeftColor: config.accent, borderLeftWidth: '4px' }}
    >
      <div className="flex items-start gap-3">
        <Icon aria-hidden="true" className="mt-0.5 h-5 w-5 flex-shrink-0" style={{ color: config.accent }} />
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
