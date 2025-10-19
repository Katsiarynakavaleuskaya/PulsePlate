/**
 * Feature Flags Configuration
 *
 * Centralized feature flag management for conditional feature enabling/disabling.
 * Flags are controlled via environment variables and provide type-safe access.
 */

/**
 * Feature flag values from environment variables
 */
const getFeatureFlagsInternal = (env: ImportMetaEnv = import.meta.env) => {
  return {
    // VIP Module - enables VIP-specific features
    vipModule: env.VITE_VIP_MODULE_ENABLED === 'true',

    // Analytics - enables user analytics tracking
    analytics: env.VITE_ANALYTICS_ENABLED !== 'false', // default: true

    // Development features
    devMode: env.DEV === true,
  } as const;
};

/**
 * Type-safe feature flags
 */
export type FeatureFlags = ReturnType<typeof getFeatureFlagsInternal>;

/**
 * Get current feature flags
 *
 * @returns Object containing all feature flag values
 *
 * @example
 * ```typescript
 * const flags = getFeatureFlags();
 * if (flags.vipModule) {
 *   // Show VIP features
 * }
 * ```
 */
export const getFeatureFlags = () => FLAGS;

/**
 * Cached feature flags (evaluated once at module load)
 */
const FLAGS = getFeatureFlagsInternal();

/**
 * Individual feature flag getters for convenience
 */
export const isVipModuleEnabled = () => FLAGS.vipModule;
export const isAnalyticsEnabled = () => FLAGS.analytics;
export const isDevMode = () => FLAGS.devMode;

/**
 * Feature flag names for debugging and analytics
 */
export const FEATURE_FLAG_NAMES = {
  VIP_MODULE: 'vipModule',
  ANALYTICS: 'analytics',
  DEV_MODE: 'devMode',
} as const;

export type FeatureFlagName = (typeof FEATURE_FLAG_NAMES)[keyof typeof FEATURE_FLAG_NAMES];
