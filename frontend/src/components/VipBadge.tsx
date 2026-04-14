import React, { useEffect, useRef } from 'react';
import clsx from 'clsx';
import { useTranslation } from 'react-i18next';
import { useVipModule } from '../lib/useFeatureFlag';
import { useTelemetry } from '../lib/useTelemetry';

export interface VipBadgeProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline' | 'subtle';
  component?: string; // For telemetry tracking
}

// Move class objects to module scope to avoid allocations on every render
const sizeClasses = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm'
};

const variantClasses = {
  default:
    'bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-success)] text-white',
  outline:
    'border border-[var(--color-primary)] text-[var(--color-primary)] dark:text-[var(--color-primary-dark)]',
  subtle:
    'bg-[var(--color-navy-50)] text-[var(--color-primary)] dark:bg-[var(--color-navy-800)] dark:text-[var(--color-blue-200)]',
};

/**
 * VIP Badge component
 *
 * Shows a VIP badge when VIP module is enabled
 */
export const VipBadge: React.FC<VipBadgeProps> = ({ size = 'md', variant = 'default', component = 'unknown' }) => {
  const isVipEnabled = useVipModule();
  const { t } = useTranslation();
  const { track } = useTelemetry();
  const { badgeViewed } = track;
  const hasTracked = useRef(false);

  // Track badge view on mount (only once)
  useEffect(() => {
    if (isVipEnabled && !hasTracked.current) {
      badgeViewed(component, variant);
      hasTracked.current = true;
    }
  }, [isVipEnabled, badgeViewed, component, variant]);

  if (!isVipEnabled) {
    return null;
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        sizeClasses[size],
        variantClasses[variant]
      )}
      aria-label={t('vip.badgeAria')}
    >
      {t('vip.badge')}
    </span>
  );
};
