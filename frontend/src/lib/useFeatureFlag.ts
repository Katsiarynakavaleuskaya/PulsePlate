/**
 * Feature Flag Hook
 *
 * React hook for accessing feature flags from environment variables.
 * Provides type-safe access to feature flags throughout the application.
 * Note: Flags are read at initialization and are static for the app lifecycle.
 * Changes require rebuild/reload or a different dynamic source.
 */

import { useMemo } from 'react';
import { getFeatureFlags, type FeatureFlags, type FeatureFlagName } from '../config/features';

/**
 * Hook to access feature flags
 *
 * @returns Object containing all feature flag values
 *
 * @example
 * ```typescript
 * function MyComponent() {
 *   const flags = useFeatureFlag();
 *
 *   return (
 *     <div>
 *       {flags.vipModule && <VipFeature />}
 *       {flags.analytics && <AnalyticsTracker />}
 *     </div>
 *   );
 * }
 * ```
 */
export const useFeatureFlag = (): FeatureFlags => {
  return useMemo(() => getFeatureFlags(), []);
};

/**
 * Hook to check a specific feature flag
 *
 * @param flagName - Name of the feature flag to check
 * @returns Boolean value of the feature flag
 *
 * @example
 * ```typescript
 * function VipComponent() {
 *   const isVipEnabled = useFeatureFlagValue('vipModule');
 *
 *   if (!isVipEnabled) {
 *     return <PremiumGate />;
 *   }
 *
 *   return <VipContent />;
 * }
 * ```
 */
export const useFeatureFlagValue = (flagName: FeatureFlagName): boolean => {
  const flags = useFeatureFlag();
  return flags[flagName];
};

/**
 * Hook to check if VIP module is enabled
 *
 * @returns Boolean indicating if VIP module is enabled
 *
 * @example
 * ```typescript
 * function ConditionalVipFeature() {
 *   const isVipEnabled = useVipModule();
 *
 *   return isVipEnabled ? <VipFeature /> : null;
 * }
 * ```
 */
export const useVipModule = (): boolean => {
  return useFeatureFlagValue('vipModule');
};

/**
 * Hook to check if analytics is enabled
 *
 * @returns Boolean indicating if analytics is enabled
 *
 * @example
 * ```typescript
 * function AnalyticsWrapper({ children }: { children: React.ReactNode }) {
 *   const isAnalyticsEnabled = useAnalytics();
 *
 *   return (
 *     <>
 *       {children}
 *       {isAnalyticsEnabled && <AnalyticsScript />}
 *     </>
 *   );
 * }
 * ```
 */
export const useAnalytics = (): boolean => {
  return useFeatureFlagValue('analytics');
};
