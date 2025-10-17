/**
 * Centralized Telemetry Event Registry
 *
 * This module centralizes all telemetry event definitions to prevent
 * accidental divergence and ensure consistency across the application.
 *
 * When adding new events:
 * 1. Define the event type in EventType enum
 * 2. Define the payload type in EventPayloadMap
 * 3. Add tracking function in vipTelemetry object
 * 4. Update this registry
 */

export enum EventType {
  // VIP Module Events
  VIP_MODULE_VIEWED = 'vip_module_viewed',
  VIP_FEATURE_CLICKED = 'vip_feature_clicked',
  VIP_PAYWALL_VIEWED = 'vip_paywall_viewed',
  VIP_PAYWALL_DISMISSED = 'vip_paywall_dismissed',
  VIP_UPGRADE_CLICKED = 'vip_upgrade_clicked',
  VIP_GATE_INTERACTED = 'vip_gate_interacted',
  VIP_BADGE_VIEWED = 'vip_badge_viewed',

  // Future Events (add here as needed)
  // TARGETS_OPENED = 'targets_opened',
  // PLAN_GENERATED = 'plan_generated',
  // SHOPLIST_OPENED = 'shoplist_opened',
  // AUTOREPAIR_CLICKED = 'autorepair_clicked',
}

export interface BaseEventPayload {
  timestamp?: number;
  sessionId?: string;
  featureFlags?: Record<string, boolean>;
}

export interface VipModuleViewedPayload extends BaseEventPayload {
  source: string;
  vipEnabled: boolean;
}

export interface VipFeatureClickedPayload extends BaseEventPayload {
  featureName: string;
  source: string;
  isVip: boolean;
}

export interface VipPaywallViewedPayload extends BaseEventPayload {
  source: string;
  context: string;
  isRetry?: boolean;
}

export interface VipPaywallDismissedPayload extends BaseEventPayload {
  source: string;
  dismissMethod: string;
  viewDuration?: number;
}

export interface VipUpgradeClickedPayload extends BaseEventPayload {
  source: string;
  context: string;
  isRetry?: boolean;
}

export interface VipGateInteractedPayload extends BaseEventPayload {
  featureName: string;
  interactionType: string;
  isVip: boolean;
}

export interface VipBadgeViewedPayload extends BaseEventPayload {
  component: string;
  variant: string;
  isVip: boolean;
}

// Centralized event payload mapping
export interface EventPayloadMap {
  [EventType.VIP_MODULE_VIEWED]: VipModuleViewedPayload;
  [EventType.VIP_FEATURE_CLICKED]: VipFeatureClickedPayload;
  [EventType.VIP_PAYWALL_VIEWED]: VipPaywallViewedPayload;
  [EventType.VIP_PAYWALL_DISMISSED]: VipPaywallDismissedPayload;
  [EventType.VIP_UPGRADE_CLICKED]: VipUpgradeClickedPayload;
  [EventType.VIP_GATE_INTERACTED]: VipGateInteractedPayload;
  [EventType.VIP_BADGE_VIEWED]: VipBadgeViewedPayload;
}

/**
 * Event Registry Configuration
 *
 * This object defines the structure and validation rules for all events.
 * Use this as the single source of truth for event definitions.
 */
export const EVENT_REGISTRY = {
  [EventType.VIP_MODULE_VIEWED]: {
    description: 'User viewed VIP module',
    requiredFields: ['source', 'vipEnabled'],
    optionalFields: [],
  },
  [EventType.VIP_FEATURE_CLICKED]: {
    description: 'User clicked on VIP feature',
    requiredFields: ['featureName', 'source', 'isVip'],
    optionalFields: [],
  },
  [EventType.VIP_PAYWALL_VIEWED]: {
    description: 'User viewed VIP paywall',
    requiredFields: ['source', 'context'],
    optionalFields: ['isRetry'],
  },
  [EventType.VIP_PAYWALL_DISMISSED]: {
    description: 'User dismissed VIP paywall',
    requiredFields: ['source', 'dismissMethod'],
    optionalFields: ['viewDuration'],
  },
  [EventType.VIP_UPGRADE_CLICKED]: {
    description: 'User clicked VIP upgrade button',
    requiredFields: ['source', 'context'],
    optionalFields: ['isRetry'],
  },
  [EventType.VIP_GATE_INTERACTED]: {
    description: 'User interacted with VIP gate',
    requiredFields: ['featureName', 'interactionType', 'isVip'],
    optionalFields: [],
  },
  [EventType.VIP_BADGE_VIEWED]: {
    description: 'User viewed VIP badge',
    requiredFields: ['component', 'variant', 'isVip'],
    optionalFields: [],
  },
} as const;

/**
 * Validation function for event payloads
 */
export function validateEventPayload<T extends EventType>(
  eventType: T,
  payload: EventPayloadMap[T]
): boolean {
  const config = EVENT_REGISTRY[eventType];
  if (!config) {
    console.error(`Unknown event type: ${eventType}`);
    return false;
  }

  // Check required fields
  for (const field of config.requiredFields) {
    if (!(field in payload) || payload[field as keyof EventPayloadMap[T]] === undefined) {
      console.error(`Missing required field '${field}' for event '${eventType}'`);
      return false;
    }
  }

  return true;
}

/**
 * Get all available event types
 */
export function getAllEventTypes(): EventType[] {
  return Object.values(EventType);
}

/**
 * Get event configuration
 */
export function getEventConfig(eventType: EventType) {
  return EVENT_REGISTRY[eventType];
}
