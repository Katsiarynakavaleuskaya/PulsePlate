import type { ButtonHTMLAttributes, JSX } from 'react';
import { Download } from 'lucide-react';

interface ProgressExportPdfButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {}

export function ProgressExportPdfButton({
  className = '',
  type = 'button',
  ...props
}: ProgressExportPdfButtonProps): JSX.Element {
  return (
    <button
      type={type}
      className={[
        'flex items-center gap-2 rounded-lg px-4 py-2 transition-colors hover:opacity-90',
        className,
      ].join(' ').trim()}
      style={{
        backgroundColor: 'var(--color-primary)',
        color: 'var(--color-primary-foreground)',
      }}
      aria-label="Export progress report as PDF"
      {...props}
    >
      <Download className="h-4 w-4" />
      Export PDF
    </button>
  );
}

export default ProgressExportPdfButton;
