import React, { useEffect } from 'react';
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
  default: 'bg-gradient-to-r from-purple-500 to-pink-500 text-white',
  outline: 'border border-purple-500 text-purple-600 dark:text-purple-400',
  subtle: 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200'
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

  // Track badge view on mount
  useEffect(() => {
    if (isVipEnabled) {
      track.badgeViewed(component, variant);
    }
  }, [isVipEnabled, track, component, variant]);

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
