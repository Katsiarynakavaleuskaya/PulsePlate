import type { PropsWithChildren, ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
}

export function Dialog({ open, onClose, title, children }: PropsWithChildren<DialogProps>) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[var(--z-modal)] grid place-items-center bg-black/50 p-4" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-lg rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] shadow-xl"
      >
        {(title || onClose) && (
          <header className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-1 text-sm text-[var(--color-text-muted)] hover:bg-[var(--color-surface-muted)]"
            >
              Close
            </button>
          </header>
        )}
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export default Dialog;
