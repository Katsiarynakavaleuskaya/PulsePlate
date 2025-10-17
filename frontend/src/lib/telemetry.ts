/**
 * Telemetry Foundation
 *
 * Centralized telemetry system for VIP events and user analytics.
 * Provides type-safe event tracking with automatic feature flag integration.
 *
 * Uses centralized event registry to prevent event definition divergence.
 */

import { log } from './analytics';
import { isAnalyticsEnabled } from '../config/features';
import { getSessionId, refreshSession, clearSession } from './sessionManager';
import { getCurrentFeatureFlags, initializeFeatureFlags, updateFeatureFlags, clearFeatureFlags } from './featureFlagManager';
import {
  EventType,
  EventPayloadMap,
  validateEventPayload,
  type BaseEventPayload,
  type VipModuleViewedPayload,
  type VipFeatureClickedPayload,
  type VipPaywallViewedPayload,
  type VipPaywallDismissedPayload,
  type VipUpgradeClickedPayload,
  type VipGateInteractedPayload,
  type VipBadgeViewedPayload,
} from './telemetry/eventRegistry';

/**
 * VIP-specific event types (imported from centralized registry)
 */
export type VipEventType = EventType;

// Re-export EventType and registry helpers for external use
export { EventType, getAllEventTypes, getEventConfig } from './telemetry/eventRegistry';

// Re-export types for backward compatibility
export type {
  BaseEventPayload,
  VipModuleViewedPayload,
  VipFeatureClickedPayload,
  VipPaywallViewedPayload,
  VipPaywallDismissedPayload,
  VipUpgradeClickedPayload,
  VipGateInteractedPayload,
  VipBadgeViewedPayload,
  EventPayloadMap,
};

/**
 * Union type for all VIP event payloads
 */
export type VipEventPayload =
  | VipModuleViewedPayload
  | VipFeatureClickedPayload
  | VipPaywallViewedPayload
  | VipPaywallDismissedPayload
  | VipUpgradeClickedPayload
  | VipGateInteractedPayload
  | VipBadgeViewedPayload;

/**
 * Core telemetry tracking function
 */
export function trackVipEvent<T extends EventType>(
  eventType: T,
  payload: EventPayloadMap[T]
): void {
  if (!isAnalyticsEnabled()) {
    return;
  }

  // Validate payload using centralized registry
  if (!validateEventPayload(eventType, payload)) {
    return; // validation already logged details
  }

  // Enrich payload with session and feature flag data
  const enrichedPayload = {
    ...payload,
    timestamp: payload.timestamp || Date.now(),
    sessionId: getSessionId(),
    featureFlags: getCurrentFeatureFlags(),
  };

  // Log the event
  log(eventType, enrichedPayload as unknown as Record<string, unknown>);
}

/**
 * VIP telemetry tracking functions
 */
export const vipTelemetry = {
  /**
   * Track VIP module view
   */
  moduleViewed: (source: string, vipEnabled: boolean) => {
    trackVipEvent(EventType.VIP_MODULE_VIEWED, {
      source,
      vipEnabled,
    });
  },

  /**
   * Track VIP feature click
   */
  featureClicked: (featureName: string, source: string, isVip: boolean) => {
    trackVipEvent(EventType.VIP_FEATURE_CLICKED, {
      featureName,
      source,
      isVip,
    });
  },

  /**
   * Track VIP paywall view
   */
  paywallViewed: (source: string, context: string, isRetry?: boolean) => {
    trackVipEvent(EventType.VIP_PAYWALL_VIEWED, {
      source,
      context,
      isRetry,
    });
  },

  /**
   * Track VIP paywall dismissal
   */
  paywallDismissed: (source: string, dismissMethod: string, viewDuration?: number) => {
    trackVipEvent(EventType.VIP_PAYWALL_DISMISSED, {
      source,
      dismissMethod,
      viewDuration,
    });
  },

  /**
   * Track VIP upgrade click
   */
  upgradeClicked: (source: string, context: string, isRetry?: boolean) => {
    trackVipEvent(EventType.VIP_UPGRADE_CLICKED, {
      source,
      context,
      isRetry,
    });
  },

  /**
   * Track VIP gate interaction
   */
  gateInteracted: (featureName: string, interactionType: string, isVip: boolean) => {
    trackVipEvent(EventType.VIP_GATE_INTERACTED, {
      featureName,
      interactionType,
      isVip,
    });
  },

  /**
   * Track VIP badge view
   */
  badgeViewed: (component: string, variant: string, isVip: boolean) => {
    trackVipEvent(EventType.VIP_BADGE_VIEWED, {
      component,
      variant,
      isVip,
    });
  },
};

/**
 * Initialize telemetry system
 */
export function initializeTelemetry(): void {
  initializeFeatureFlags();
  if (isAnalyticsEnabled()) {
    refreshSession();
  }
}

/**
 * Update feature flags for telemetry
 */
export function updateTelemetryFeatureFlags(flags: Record<string, boolean>): void {
  updateFeatureFlags(flags);
}

/**
 * Refresh telemetry session
 */
export function refreshTelemetrySession(): string | 'disabled' {
  if (!isAnalyticsEnabled()) {
    return 'disabled';
  }

  return refreshSession();
}

/**
 * Clear telemetry data
 */
export function clearTelemetryData(): void {
  clearSession();
  clearFeatureFlags();
}

/**
 * Check if telemetry is enabled
 */
export function isTelemetryEnabled(): boolean {
  return isAnalyticsEnabled();
}
