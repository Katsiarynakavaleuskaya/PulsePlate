/**
 * VIP Feature Component
 *
 * Example component that demonstrates VIP feature flag integration.
 * This component will only render when VIP module is enabled.
 */

import React from 'react';
import { useVipModule } from '../lib/useFeatureFlag';

interface VipFeatureProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * VIP Feature wrapper component
 *
 * @param children - Content to show when VIP is enabled
 * @param fallback - Content to show when VIP is disabled (optional)
 *
 * @example
 * ```typescript
 * <VipFeature fallback={<PremiumGate />}>
 *   <AdvancedAnalytics />
 * </VipFeature>
 * ```
 */
export const VipFeature: React.FC<VipFeatureProps> = ({ children, fallback = null }) => {
  const isVipEnabled = useVipModule();

  if (!isVipEnabled) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};

// Re-export all VIP components for backward compatibility
export { VipBadge } from './VipBadge';
export { VipGate } from './VipGate';
export { VipPageHeader } from './VipPageHeader';
export { VipFeatureCard } from './VipFeatureCard';
export { VipSection } from './VipSection';
