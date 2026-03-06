import type { ButtonHTMLAttributes, PropsWithChildren } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'destructive';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--color-primary)] text-[var(--color-primary-foreground)] hover:opacity-95 hover:shadow-md',
  secondary:
    'border border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text)] hover:bg-[var(--color-surface)] hover:shadow-sm',
  ghost: 'bg-transparent text-[var(--color-text)] hover:bg-[var(--color-surface-muted)]',
  destructive:
    'border border-[rgba(255,93,93,0.18)] bg-[rgba(255,93,93,0.1)] text-[var(--pp-red)] hover:bg-[rgba(255,93,93,0.14)] hover:shadow-[0_12px_32px_rgba(255,93,93,0.12)]',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'min-h-[40px] px-4 py-2 text-sm',
  md: 'min-h-[44px] px-6 py-3 text-sm',
  lg: 'min-h-[48px] px-6 py-4 text-base',
};

export function buttonClasses({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  className = '',
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  className?: string;
}) {
  return [
    'rounded-xl font-semibold transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-60',
    variantClasses[variant],
    sizeClasses[size],
    fullWidth ? 'w-full' : '',
    className,
  ]
    .join(' ')
    .trim();
}

export function Button({
  children,
  className = '',
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  type = 'button',
  ...props
}: PropsWithChildren<ButtonProps>) {
  return (
    <button
      className={buttonClasses({ variant, size, fullWidth, className })}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}

export default Button;
