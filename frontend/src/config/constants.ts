/**
 * Constants for premium gate sources
 *
 * These constants are used to track where premium gates are triggered from
 * for analytics and debugging purposes.
 */
export const PREMIUM_GATE_SOURCES = {
  PLATE_PAGE: 'plate_page',
  // Add other premium gate sources here as needed
  // PROGRESS_PAGE: 'progress_page',
  // PROFILE_PAGE: 'profile_page',
} as const;

// Type for premium gate source values
export type PremiumGateSource = (typeof PREMIUM_GATE_SOURCES)[keyof typeof PREMIUM_GATE_SOURCES];
