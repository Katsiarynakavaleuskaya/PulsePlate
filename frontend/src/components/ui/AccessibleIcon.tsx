import { cn } from '@/lib/utils';
import React from 'react';

interface AccessibleIconProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string; // Обязательный параметр
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  role?: string;
  'aria-hidden'?: boolean;
}

/**
 * AccessibleIcon - компонент иконки с обязательной доступностью
 *
 * Требует обязательный label для обеспечения доступности.
 * Если label не предоставлен, выбрасывает ошибку в development режиме.
 */
export const AccessibleIcon: React.FC<AccessibleIconProps> = ({
  icon: Icon,
  label,
  className,
  size = 'md',
  role: _role = 'img',
  'aria-hidden': ariaHidden = false,
  ...props
}) => {
  // Проверка в development режиме
  if (process.env.NODE_ENV === 'development' && !label?.trim()) {
    throw new Error(
      'AccessibleIcon: label is required for accessibility. ' +
      'Please provide a descriptive label for screen readers.'
    );
  }

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  return (
    <Icon
      className={cn(sizeClasses[size], className)}
      aria-label={label}
      aria-hidden={ariaHidden}
      {...props}
    />
  );
};

/**
 * SvgIcon - компонент для SVG иконок с обязательной доступностью
 */
interface SvgIconProps {
  children: React.ReactNode;
  label: string; // Обязательный параметр
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  role?: string;
  'aria-hidden'?: boolean;
}

export const SvgIcon: React.FC<SvgIconProps> = ({
  children,
  label,
  className,
  size = 'md',
  role = 'img',
  'aria-hidden': ariaHidden = false,
}) => {
  // Проверка в development режиме
  if (process.env.NODE_ENV === 'development' && !label?.trim()) {
    throw new Error(
      'SvgIcon: label is required for accessibility. ' +
      'Please provide a descriptive label for screen readers.'
    );
  }

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  return (
    <svg
      className={cn(sizeClasses[size], className)}
      role={role}
      aria-label={label}
      aria-hidden={ariaHidden}
      fill="currentColor"
      viewBox="0 0 24 24"
    >
      {children}
    </svg>
  );
};

/**
 * ImageIcon - компонент для изображений с обязательной доступностью
 */
interface ImageIconProps {
  src: string;
  alt: string; // Обязательный параметр
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  role?: string;
  'aria-hidden'?: boolean;
}

export const ImageIcon: React.FC<ImageIconProps> = ({
  src,
  alt,
  className,
  size = 'md',
  role = 'img',
  'aria-hidden': ariaHidden = false,
}) => {
  // Проверка в development режиме
  if (process.env.NODE_ENV === 'development' && !alt?.trim()) {
    throw new Error(
      'ImageIcon: alt is required for accessibility. ' +
      'Please provide a descriptive alt text for screen readers.'
    );
  }

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  return (
    <img
      src={src}
      alt={alt}
      className={cn(sizeClasses[size], className)}
      role={role}
      aria-hidden={ariaHidden}
    />
  );
};
