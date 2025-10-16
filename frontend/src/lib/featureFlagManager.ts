/**
 * Feature Flag Manager for Telemetry
 *
 * Captures and maintains current feature flag state for telemetry events.
 * Provides privacy-safe flag state management with automatic updates.
 */

import { getFeatureFlags } from '../config/features';

// Store current feature flag state
let currentFeatureFlags: Record<string, boolean> = {};

/**
 * Initialize feature flags from current configuration
 */
export function initializeFeatureFlags(): void {
  try {
    const flags = getFeatureFlags();
    currentFeatureFlags = { ...flags };
  } catch (error) {
    console.warn('[Telemetry] Failed to initialize feature flags:', error);
    currentFeatureFlags = {};
  }
}

/**
 * Update feature flags state
 * @param flagState - New feature flag state
 */
export function updateFeatureFlags(flagState: Record<string, boolean>): void {
  try {
    // Sanitize flag names to prevent PII leakage
    const sanitizedFlags: Record<string, boolean> = {};

    for (const [key, value] of Object.entries(flagState)) {
      // Only include known feature flag keys
      if (isValidFeatureFlagKey(key)) {
        sanitizedFlags[key] = Boolean(value);
      }
    }

    currentFeatureFlags = { ...sanitizedFlags };
  } catch (error) {
    console.warn('[Telemetry] Failed to update feature flags:', error);
  }
}

/**
 * Get current feature flags state
 */
export function getCurrentFeatureFlags(): Record<string, boolean> {
  return { ...currentFeatureFlags };
}

/**
 * Check if a flag key is valid (prevents PII leakage)
 */
function isValidFeatureFlagKey(key: string): boolean {
  // Only allow known feature flag patterns
  const validPatterns = [
    /^vipModule$/,
    /^analytics$/,
    /^devMode$/,
    /^[a-z][a-zA-Z0-9]*$/, // Standard camelCase identifiers (lowercase-starting)
  ];

  return validPatterns.some(pattern => pattern.test(key));
}

/**
 * Refresh feature flags from current configuration
 */
export function refreshFeatureFlags(): void {
  initializeFeatureFlags();
}

/**
 * Clear feature flags (for privacy)
 */
export function clearFeatureFlags(): void {
  currentFeatureFlags = {};
}
