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

  // Growth Funnel Events
  ONBOARDING_STARTED = 'onboarding_started',
  ONBOARDING_COMPLETED = 'onboarding_completed',
  PAYWALL_VIEWED = 'paywall_viewed',
  PAYWALL_CTA_CLICKED = 'paywall_cta_clicked',
  TRIAL_STARTED = 'trial_started',
  RETENTION_HEARTBEAT = 'retention_heartbeat',

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

export interface OnboardingStartedPayload extends BaseEventPayload {
  source: string;
  variant: string;
}

export interface OnboardingCompletedPayload extends BaseEventPayload {
  source: string;
  durationSec?: number;
}

export interface PaywallViewedPayload extends BaseEventPayload {
  source: string;
  placement: string;
  tierContext: 'free' | 'pro' | 'vip';
}

export interface PaywallCtaClickedPayload extends BaseEventPayload {
  source: string;
  ctaId: string;
  tierContext: 'free' | 'pro' | 'vip';
}

export interface TrialStartedPayload extends BaseEventPayload {
  source: string;
  planType: string;
}

export interface RetentionHeartbeatPayload extends BaseEventPayload {
  dayBucket: 'd1' | 'd7' | 'd30';
  source: string;
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
  [EventType.ONBOARDING_STARTED]: OnboardingStartedPayload;
  [EventType.ONBOARDING_COMPLETED]: OnboardingCompletedPayload;
  [EventType.PAYWALL_VIEWED]: PaywallViewedPayload;
  [EventType.PAYWALL_CTA_CLICKED]: PaywallCtaClickedPayload;
  [EventType.TRIAL_STARTED]: TrialStartedPayload;
  [EventType.RETENTION_HEARTBEAT]: RetentionHeartbeatPayload;
}

type PrimitiveFieldType = 'string' | 'number' | 'boolean';

type EventFieldSchema = {
  type: PrimitiveFieldType;
  required: boolean;
  enum?: readonly string[];
};

const TIER_CONTEXT_ENUM = ['free', 'pro', 'vip'] as const;
const RETENTION_DAY_BUCKET_ENUM = ['d1', 'd7', 'd30'] as const;


/**
 * Event Registry Configuration with type-safe validation
 *
 * This object defines the structure and validation rules for all events.
 * Use this as the single source of truth for event definitions.
 */
export const EVENT_REGISTRY = {
  [EventType.VIP_MODULE_VIEWED]: {
    description: 'User viewed VIP module',
    fields: {
      source: { type: 'string', required: true },
      vipEnabled: { type: 'boolean', required: true },
    },
  },
  [EventType.VIP_FEATURE_CLICKED]: {
    description: 'User clicked on VIP feature',
    fields: {
      featureName: { type: 'string', required: true },
      source: { type: 'string', required: true },
      isVip: { type: 'boolean', required: true },
    },
  },
  [EventType.VIP_PAYWALL_VIEWED]: {
    description: 'User viewed VIP paywall',
    fields: {
      source: { type: 'string', required: true },
      context: { type: 'string', required: true },
      isRetry: { type: 'boolean', required: false },
    },
  },
  [EventType.VIP_PAYWALL_DISMISSED]: {
    description: 'User dismissed VIP paywall',
    fields: {
      source: { type: 'string', required: true },
      dismissMethod: { type: 'string', required: true },
      viewDuration: { type: 'number', required: false },
    },
  },
  [EventType.VIP_UPGRADE_CLICKED]: {
    description: 'User clicked VIP upgrade button',
    fields: {
      source: { type: 'string', required: true },
      context: { type: 'string', required: true },
      isRetry: { type: 'boolean', required: false },
    },
  },
  [EventType.VIP_GATE_INTERACTED]: {
    description: 'User interacted with VIP gate',
    fields: {
      featureName: { type: 'string', required: true },
      interactionType: { type: 'string', required: true },
      isVip: { type: 'boolean', required: true },
    },
  },
  [EventType.VIP_BADGE_VIEWED]: {
    description: 'User viewed VIP badge',
    fields: {
      component: { type: 'string', required: true },
      variant: { type: 'string', required: true },
      isVip: { type: 'boolean', required: true },
    },
  },
  [EventType.ONBOARDING_STARTED]: {
    description: 'User started onboarding flow',
    fields: {
      source: { type: 'string', required: true },
      variant: { type: 'string', required: true },
    },
  },
  [EventType.ONBOARDING_COMPLETED]: {
    description: 'User completed onboarding flow',
    fields: {
      source: { type: 'string', required: true },
      durationSec: { type: 'number', required: false },
    },
  },
  [EventType.PAYWALL_VIEWED]: {
    description: 'User viewed paywall in growth funnel',
    fields: {
      source: { type: 'string', required: true },
      placement: { type: 'string', required: true },
      tierContext: { type: 'string', required: true, enum: TIER_CONTEXT_ENUM },
    },
  },
  [EventType.PAYWALL_CTA_CLICKED]: {
    description: 'User clicked paywall CTA',
    fields: {
      source: { type: 'string', required: true },
      ctaId: { type: 'string', required: true },
      tierContext: { type: 'string', required: true, enum: TIER_CONTEXT_ENUM },
    },
  },
  [EventType.TRIAL_STARTED]: {
    description: 'User started trial from paywall',
    fields: {
      source: { type: 'string', required: true },
      planType: { type: 'string', required: true },
    },
  },
  [EventType.RETENTION_HEARTBEAT]: {
    description: 'Retention heartbeat event for cohort analysis',
    fields: {
      dayBucket: { type: 'string', required: true, enum: RETENTION_DAY_BUCKET_ENUM },
      source: { type: 'string', required: true },
    },
  },
} as const;

/**
 * Type-safe runtime validation function for event payloads
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

  // Basic runtime guard
  if (payload === null || typeof payload !== 'object') {
    console.error(`Invalid payload for event '${eventType}': expected object`);
    return false;
  }

  // Validate BaseEventPayload fields if present
  if ('timestamp' in payload && typeof payload.timestamp !== 'number') {
    console.error(`Invalid type for 'timestamp': expected 'number', got '${typeof payload.timestamp}'`);
    return false;
  }
  if ('sessionId' in payload && typeof payload.sessionId !== 'string') {
    console.error(`Invalid type for 'sessionId': expected 'string', got '${typeof payload.sessionId}'`);
    return false;
  }
  if ('featureFlags' in payload && (payload.featureFlags === null || typeof payload.featureFlags !== 'object' || Array.isArray(payload.featureFlags))) {
    console.error(`Invalid type for 'featureFlags': expected 'object', got '${typeof payload.featureFlags}'`);
    return false;
  }

      // Validate featureFlags values are booleans
      if ('featureFlags' in payload && payload.featureFlags) {
        for (const [key, value] of Object.entries(payload.featureFlags)) {
          if (typeof value !== 'boolean') {
            console.error(`Invalid value type for featureFlags['${key}']: expected 'boolean', got '${typeof value}'`);
            return false;
          }
        }
      }

  // Validate each field according to its schema
  for (const [fieldName, fieldSchema] of Object.entries(config.fields)) {
    const typedFieldSchema = fieldSchema as EventFieldSchema;
    const value = payload[fieldName as keyof EventPayloadMap[T]];

    // Check if required field is missing
    if (typedFieldSchema.required && (value === undefined || value === null)) {
      console.error(`Missing required field '${fieldName}' for event '${eventType}'`);
      return false;
    }

    // Skip type validation for optional fields that are undefined
    if (!typedFieldSchema.required && value === undefined) {
      continue;
    }

    // Reject null for optional fields
    if (!typedFieldSchema.required && value === null) {
      console.error(`Field '${fieldName}' in event '${eventType}' cannot be null (use undefined for optional fields)`);
      return false;
    }

    // Perform type validation
    const actualType = getValueType(value);
    if (actualType !== typedFieldSchema.type) {
      console.error(
        `Invalid type for field '${fieldName}' in event '${eventType}': expected '${typedFieldSchema.type}', got '${actualType}'`
      );
      return false;
    }

    if (
      typedFieldSchema.enum &&
      typedFieldSchema.type === 'string' &&
      !typedFieldSchema.enum.includes(String(value))
    ) {
      console.error(
        `Invalid value for field '${fieldName}' in event '${eventType}': expected one of [${typedFieldSchema.enum.join(', ')}], got '${String(value)}'`
      );
      return false;
    }
  }

  return true;
}

/**
 * Get the runtime type of a value for validation
 */
function getValueType(value: unknown): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  return typeof value;
}

/**
 * Get all available event types
 */
export function getAllEventTypes(): EventType[] {
  return Object.values(EventType) as EventType[];
}

/**
 * Get event configuration
 */
export function getEventConfig(eventType: EventType) {
  return EVENT_REGISTRY[eventType];
}

/**
 * Get required fields for an event type (for backward compatibility)
 */
export function getRequiredFields(eventType: EventType): string[] {
  const config = EVENT_REGISTRY[eventType];
  if (!config) return [];

  return Object.entries(config.fields)
    .filter(([, schema]) => schema.required)
    .map(([fieldName]) => fieldName);
}

/**
 * Get optional fields for an event type (for backward compatibility)
 */
export function getOptionalFields(eventType: EventType): string[] {
  const config = EVENT_REGISTRY[eventType];
  if (!config) return [];

  return Object.entries(config.fields)
    .filter(([, schema]) => !schema.required)
    .map(([fieldName]) => fieldName);
}
