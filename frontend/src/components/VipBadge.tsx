import React, { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useVipModule } from '../lib/useFeatureFlag';
import { useTelemetry } from '../lib/useTelemetry';
import { Badge } from './ui';

export interface VipBadgeProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline' | 'subtle';
  component?: string; // For telemetry tracking
}

const variantToSharedVariant = {
  default: 'solid',
  outline: 'outline',
  subtle: 'subtle',
} as const;

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
    <Badge
      data-testid="vip-badge"
      aria-label={t('vip.badgeAria')}
      size={size}
      tone="premium"
      variant={variantToSharedVariant[variant]}
    >
      {t('vip.badge')}
    </Badge>
  );
};
