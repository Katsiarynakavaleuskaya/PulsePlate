/**
 * React Hook for VIP Telemetry
 *
 * Provides convenient access to VIP telemetry functions within React components.
 * Automatically handles feature flag checks and provides type-safe event tracking.
 */

import { useCallback } from 'react';
import { vipTelemetry, isTelemetryEnabled } from './telemetry';
import { useVipModule } from './useFeatureFlag';

/**
 * Hook for VIP telemetry functionality
 *
 * @returns Object with telemetry functions and enabled state
 *
 * @example
 * ```typescript
 * function VipFeature() {
 *   const { track, isEnabled } = useTelemetry();
 *
 *   const handleFeatureClick = () => {
 *     track.featureClicked('advanced_analytics', 'dashboard', false);
 *   };
 *
 *   return (
 *     <button onClick={handleFeatureClick}>
 *       Advanced Analytics
 *     </button>
 *   );
 * }
 * ```
 */
export function useTelemetry() {
  const isVip = useVipModule();
  const isEnabled = isTelemetryEnabled();

  const track = {
    /**
     * Track VIP module view
     */
    moduleViewed: useCallback((source: string) => {
      if (!isEnabled) return;
      vipTelemetry.moduleViewed(source, isVip);
    }, [isEnabled, isVip]),

    /**
     * Track VIP feature click
     */
    featureClicked: useCallback((featureName: string, source: string) => {
      if (!isEnabled) return;
      vipTelemetry.featureClicked(featureName, source, isVip);
    }, [isEnabled, isVip]),

    /**
     * Track paywall view
     */
    paywallViewed: useCallback((source: string, context: string, isRetry?: boolean) => {
      if (!isEnabled) return;
      vipTelemetry.paywallViewed(source, context, isRetry);
    }, [isEnabled]),

    /**
     * Track paywall dismissal
     */
    paywallDismissed: useCallback((source: string, dismissMethod: string, viewDuration?: number) => {
      if (!isEnabled) return;
      vipTelemetry.paywallDismissed(source, dismissMethod, viewDuration);
    }, [isEnabled, isVip]),

    /**
     * Track upgrade click
     */
    upgradeClicked: useCallback((source: string, context: string, isRetry?: boolean) => {
      if (!isEnabled) return;
      vipTelemetry.upgradeClicked(source, context, isRetry);
    }, [isEnabled, isVip]),

    /**
     * Track VIP gate interaction
     */
    gateInteracted: useCallback((featureName: string, interactionType: string) => {
      if (!isEnabled) return;
      vipTelemetry.gateInteracted(featureName, interactionType, isVip);
    }, [isEnabled, isVip]),

    /**
     * Track VIP badge view
     */
    badgeViewed: useCallback((component: string, variant: string) => {
      if (!isEnabled) return;
      vipTelemetry.badgeViewed(component, variant, isVip);
    }, [isEnabled, isVip]),
  };

  return {
    track,
    isEnabled,
    isVip,
  };
}

/**
 * Hook for tracking VIP module views
 * Automatically tracks when component mounts if VIP module is enabled
 *
 * @param source - Source identifier for the view
 * @param autoTrack - Whether to automatically track on mount (default: true)
 *
 * @example
 * ```typescript
 * function VipDashboard() {
 *   useVipModuleTracking('dashboard');
 *
 *   return <div>VIP Dashboard</div>;
 * }
 * ```
 */
export function useVipModuleTracking(source: string, autoTrack: boolean = true) {
  const { track, isEnabled, isVip } = useTelemetry();

  const trackView = useCallback(() => {
    if (isEnabled && isVip) {
      track.moduleViewed(source);
    }
  }, [track, isEnabled, isVip, source]);

  // Auto-track on mount if enabled
  if (autoTrack) {
    trackView();
  }

  return {
    trackView,
    isEnabled,
    isVip,
  };
}
