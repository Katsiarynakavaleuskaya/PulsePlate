import { cloneElement, isValidElement, useId, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';

interface TooltipProps {
  children: ReactElement;
  content: ReactNode;
  side?: 'top' | 'bottom';
}

export function Tooltip({ children, content, side = 'top' }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();
  const positionClasses =
    side === 'bottom'
      ? 'top-full mt-2 left-1/2 -translate-x-1/2'
      : 'bottom-full mb-2 left-1/2 -translate-x-1/2';

  const child = isValidElement(children)
    ? cloneElement(children, {
        'aria-describedby': [children.props['aria-describedby'], tooltipId].filter(Boolean).join(' '),
      })
    : children;

  return (
    <span
      className="relative inline-flex"
      onBlurCapture={() => setOpen(false)}
      onFocusCapture={() => setOpen(true)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {child}
      {open ? (
        <span
          className={[
            'pointer-events-none absolute z-50 max-w-[220px] rounded-lg border border-[var(--color-border)]',
            'bg-[var(--color-surface)] px-3 py-2 text-xs leading-5 text-[var(--color-text)] shadow-lg',
            positionClasses,
          ]
            .join(' ')
            .trim()}
          id={tooltipId}
          role="tooltip"
        >
          {content}
        </span>
      ) : null}
    </span>
  );
}

export default Tooltip;
