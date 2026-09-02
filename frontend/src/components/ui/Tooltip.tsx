import { cloneElement, useId, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';

interface TooltipChildProps {
  'aria-describedby'?: string;
}

interface TooltipProps {
  children: ReactElement<TooltipChildProps>;
  content: ReactNode;
  side?: 'top' | 'bottom';
}

export function Tooltip({ children, content, side = 'top' }: TooltipProps): ReactElement {
  const [open, setOpen] = useState(false);
  const tooltipId = useId();
  const positionClasses =
    side === 'bottom'
      ? 'top-full mt-2 left-1/2 -translate-x-1/2'
      : 'bottom-full mb-2 left-1/2 -translate-x-1/2';

  const child = cloneElement(children, {
    'aria-describedby': [children.props['aria-describedby'], tooltipId].filter(Boolean).join(' '),
  });

  return (
    <span
      className="relative inline-flex"
      onBlurCapture={() => setOpen(false)}
      onFocusCapture={() => setOpen(true)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {child}
      <span
        className={[
          open ? 'pointer-events-none absolute z-50 max-w-[220px] rounded-lg border border-[var(--color-border)]' : 'sr-only',
          open ? 'bg-[var(--color-surface)] px-3 py-2 text-xs leading-5 text-[var(--color-text)] shadow-lg' : '',
          open ? positionClasses : '',
        ]
          .join(' ')
          .trim()}
        id={tooltipId}
        role="tooltip"
      >
        {content}
      </span>
    </span>
  );
}

export default Tooltip;
