/**
 * Telemetry Foundation
 *
 * Centralized telemetry system for VIP events and user analytics.
 * Provides type-safe event tracking with automatic feature flag integration.
 */

import { log } from './analytics';
import { isAnalyticsEnabled } from '../config/features';
import { getSessionId, refreshSession, clearSession } from './sessionManager';
import { getCurrentFeatureFlags, initializeFeatureFlags, updateFeatureFlags, clearFeatureFlags } from './featureFlagManager';

/**
 * VIP-specific event types
 */
export type VipEventType =
  | 'vip_module_viewed'
  | 'vip_feature_clicked'
  | 'vip_paywall_viewed'
  | 'vip_paywall_dismissed'
  | 'vip_upgrade_clicked'
  | 'vip_gate_interacted'
  | 'vip_badge_viewed';

/**
 * Base event payload structure
 */
export interface BaseEventPayload {
  /** Timestamp when event occurred */
  timestamp?: number;
  /** User session identifier */
  sessionId?: string;
  /** Feature flag state at time of event */
  featureFlags?: Record<string, boolean>;
}

/**
 * VIP-specific event payloads
 */
export interface VipModuleViewedPayload extends BaseEventPayload {
  /** Source page or component that triggered the view */
  source: string;
  /** Whether VIP module is currently enabled */
  vipEnabled: boolean;
}

export interface VipFeatureClickedPayload extends BaseEventPayload {
  /** Name of the VIP feature that was clicked */
  featureName: string;
  /** Component or page where the click occurred */
  source: string;
  /** Whether user is currently VIP */
  isVip: boolean;
}

export interface VipPaywallViewedPayload extends BaseEventPayload {
  /** Source that triggered the paywall */
  source: string;
  /** Context of the paywall (e.g., 'feature_gate', 'upgrade_prompt') */
  context: string;
  /** Whether this is a retry (user has seen paywall before) */
  isRetry?: boolean;
}

export interface VipPaywallDismissedPayload extends BaseEventPayload {
  /** Source that triggered the paywall */
  source: string;
  /** How the paywall was dismissed ('close_button', 'backdrop', 'escape') */
  dismissMethod: string;
  /** Time spent viewing paywall in milliseconds */
  viewDuration?: number;
}

export interface VipUpgradeClickedPayload extends BaseEventPayload {
  /** Source that triggered the upgrade */
  source: string;
  /** Context of the upgrade (e.g., 'paywall', 'feature_gate') */
  context: string;
  /** Whether this is a retry (user has clicked upgrade before) */
  isRetry?: boolean;
}

export interface VipGateInteractedPayload extends BaseEventPayload {
  /** Name of the gated feature */
  featureName: string;
  /** Type of interaction ('click', 'hover', 'focus') */
  interactionType: string;
  /** Whether user is currently VIP */
  isVip: boolean;
}

export interface VipBadgeViewedPayload extends BaseEventPayload {
  /** Component where badge was viewed */
  component: string;
  /** Badge variant ('small', 'medium', 'large') */
  variant: string;
  /** Whether user is currently VIP */
  isVip: boolean;
}

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
 * Type mapping for event payloads
 */
type EventPayloadMap = {
  'vip_module_viewed': Omit<VipModuleViewedPayload, 'timestamp'>;
  'vip_feature_clicked': Omit<VipFeatureClickedPayload, 'timestamp'>;
  'vip_paywall_viewed': Omit<VipPaywallViewedPayload, 'timestamp'>;
  'vip_paywall_dismissed': Omit<VipPaywallDismissedPayload, 'timestamp'>;
  'vip_upgrade_clicked': Omit<VipUpgradeClickedPayload, 'timestamp'>;
  'vip_gate_interacted': Omit<VipGateInteractedPayload, 'timestamp'>;
  'vip_badge_viewed': Omit<VipBadgeViewedPayload, 'timestamp'>;
};

/**
 * Enhanced analytics function with VIP event support
 */
export function trackVipEvent<T extends VipEventType>(
  eventType: T,
  payload: EventPayloadMap[T]
): void {
  // Only track if analytics is enabled
  if (!isAnalyticsEnabled()) {
    return;
  }

  // Get current session and feature flags
  const sessionId = getSessionId();
  const featureFlags = getCurrentFeatureFlags();

  // Add timestamp, sessionId, and featureFlags if not provided
  const enrichedPayload = {
    timestamp: Date.now(),
    sessionId,
    featureFlags,
    ...payload,
  };

  // Log the event (already has vip_ prefix)
  log(eventType, enrichedPayload);
}

/**
 * Convenience functions for common VIP events
 */
export const vipTelemetry = {
  /**
   * Track when VIP module is viewed
   */
  moduleViewed: (source: string, vipEnabled: boolean) => {
    trackVipEvent('vip_module_viewed', { source, vipEnabled });
  },

  /**
   * Track when a VIP feature is clicked
   */
  featureClicked: (featureName: string, source: string, isVip: boolean) => {
    trackVipEvent('vip_feature_clicked', { featureName, source, isVip });
  },

  /**
   * Track when paywall is viewed
   */
  paywallViewed: (source: string, context: string, isRetry?: boolean) => {
    trackVipEvent('vip_paywall_viewed', { source, context, isRetry });
  },

  /**
   * Track when paywall is dismissed
   */
  paywallDismissed: (source: string, dismissMethod: string, viewDuration?: number) => {
    trackVipEvent('vip_paywall_dismissed', { source, dismissMethod, viewDuration });
  },

  /**
   * Track when upgrade is clicked
   */
  upgradeClicked: (source: string, context: string, isRetry?: boolean) => {
    trackVipEvent('vip_upgrade_clicked', { source, context, isRetry });
  },

  /**
   * Track when VIP gate is interacted with
   */
  gateInteracted: (featureName: string, interactionType: string, isVip: boolean) => {
    trackVipEvent('vip_gate_interacted', { featureName, interactionType, isVip });
  },

  /**
   * Track when VIP badge is viewed
   */
  badgeViewed: (component: string, variant: string, isVip: boolean) => {
    trackVipEvent('vip_badge_viewed', { component, variant, isVip });
  },
};

/**
 * Utility to check if telemetry is enabled
 */
export const isTelemetryEnabled = (): boolean => {
  return isAnalyticsEnabled();
};

/**
 * Initialize telemetry system
 * Call this once at app startup
 */
export function initializeTelemetry(): void {
  if (!isAnalyticsEnabled()) {
    return;
  }

  // Initialize feature flags
  initializeFeatureFlags();

  // Ensure we have a valid session
  getSessionId();
}

/**
 * Update feature flags for telemetry
 * Call this when feature flags change
 */
export function updateTelemetryFeatureFlags(flagState: Record<string, boolean>): void {
  updateFeatureFlags(flagState);
}

/**
 * Refresh telemetry session
 * Call this periodically or on user activity
 */
export function refreshTelemetrySession(): string {
  return refreshSession();
}

/**
 * Clear telemetry data (for privacy/sign-out)
 */
export function clearTelemetryData(): void {
  clearSession();
  clearFeatureFlags();
}
