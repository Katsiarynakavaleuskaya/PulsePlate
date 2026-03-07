import type { ButtonHTMLAttributes, JSX } from 'react';
import { Download } from 'lucide-react';
import { buttonClasses } from '../ui';

/**
 * Fixed-label export CTA that accepts standard button props such as
 * onClick, disabled, and className.
 */
type ProgressExportPdfButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'>;

export function ProgressExportPdfButton({
  className = '',
  type = 'button',
  ...props
}: ProgressExportPdfButtonProps): JSX.Element {
  return (
    <button
      type={type}
      className={buttonClasses({
        variant: 'primary',
        size: 'sm',
        className: ['inline-flex items-center gap-2', className].join(' ').trim(),
      })}
      aria-label="Export progress report as PDF"
      {...props}
    >
      <Download className="h-4 w-4" />
      Export PDF
    </button>
  );
}

export default ProgressExportPdfButton;
