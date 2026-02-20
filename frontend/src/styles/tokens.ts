/**
 * Design Tokens Foundation
 *
 * Centralized design system tokens for consistent UI across the application.
 * Provides type-safe access to colors, spacing, typography, and other design values.
 */

/**
 * Canonical PulsePlate brand tokens.
 * Bridge phase uses current runtime values to avoid visual drift in PR-1.
 */
export const canonicalBrand = {
  navy: '#102a43',
  blue: '#3b82f6',
  green: '#22c55e',
  red: '#ef4444',
  gold: '#d4af37',
} as const;

/**
 * @deprecated Use canonicalBrand.* directly in new code.
 * Kept only for soft migration compatibility.
 */
export const legacyBrandAliases = {
  primary: canonicalBrand.blue,
  accent: canonicalBrand.green,
} as const;

// ============================================================================
// COLOR TOKENS
// ============================================================================

/**
 * Primary color palette
 */
export const colors = {
  // Navy theme (primary)
  navy: {
    50: '#f0f4f8',
    100: '#d9e2ec',
    200: '#bcccdc',
    300: '#9fb3c8',
    400: '#829ab1',
    500: '#627d98', // Base navy
    600: '#486581',
    700: '#334e68',
    800: '#243b53',
    900: '#102a43',
  },

  // Blue accent
  blue: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6', // Base blue
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },

  // Green success
  green: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e', // Base green
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },

  // Heart/Red accent
  heart: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444', // Base heart
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },

  // Neutral grays
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },

  // Semantic colors
  semantic: {
    success: canonicalBrand.green,
    warning: '#f59e0b',
    error: canonicalBrand.red,
    info: canonicalBrand.blue,
  },
} as const;

// ============================================================================
// SPACING TOKENS
// ============================================================================

/**
 * Spacing scale based on 4px base unit
 * 44×44pt targets for touch-friendly interfaces
 */
export const spacing = {
  // Base units
  0: '0',
  1: '0.25rem', // 4px
  2: '0.5rem',  // 8px
  3: '0.75rem', // 12px
  4: '1rem',    // 16px
  5: '1.25rem', // 20px
  6: '1.5rem',  // 24px
  8: '2rem',    // 32px
  10: '2.5rem', // 40px
  12: '3rem',   // 48px
  16: '4rem',   // 64px
  20: '5rem',   // 80px
  24: '6rem',   // 96px

  // Touch targets (44pt = 44px at 1x, 88px at 2x)
  touch: '2.75rem', // 44px
  touchLarge: '3.5rem', // 56px

  // Component specific
  button: {
    sm: '0.5rem 1rem',    // 8px 16px
    md: '0.75rem 1.5rem', // 12px 24px
    lg: '1rem 2rem',      // 16px 32px
  },

  input: {
    sm: '0.5rem 0.75rem', // 8px 12px
    md: '0.75rem 1rem',   // 12px 16px
    lg: '1rem 1.25rem',   // 16px 20px
  },
} as const;

// ============================================================================
// TYPOGRAPHY TOKENS
// ============================================================================

/**
 * Typography scale and font families
 */
export const typography = {
  // Font families
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'Consolas', 'monospace'],
  },

  // Font sizes (rem-based)
  fontSize: {
    xs: '0.75rem',   // 12px
    sm: '0.875rem',  // 14px
    base: '1rem',    // 16px
    lg: '1.125rem',  // 18px
    xl: '1.25rem',   // 20px
    '2xl': '1.5rem', // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
    '5xl': '3rem',   // 48px
  },

  // Font weights
  fontWeight: {
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },

  // Line heights
  lineHeight: {
    tight: '1.25',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
    loose: '2',
  },

  // Text styles
  textStyles: {
    heading: {
      fontFamily: 'Inter',
      fontWeight: '600',
      lineHeight: '1.25',
    },
    body: {
      fontFamily: 'Inter',
      fontWeight: '400',
      lineHeight: '1.5',
    },
    caption: {
      fontFamily: 'Inter',
      fontWeight: '400',
      lineHeight: '1.375',
      fontSize: '0.875rem',
    },
  },
} as const;

// ============================================================================
// BORDER RADIUS TOKENS
// ============================================================================

export const borderRadius = {
  none: '0',
  sm: '0.125rem',   // 2px
  base: '0.25rem',  // 4px
  md: '0.375rem',   // 6px
  lg: '0.5rem',     // 8px
  xl: '0.75rem',    // 12px
  '2xl': '1rem',    // 16px
  full: '9999px',
} as const;

// ============================================================================
// SHADOW TOKENS
// ============================================================================

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  base: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
} as const;

// ============================================================================
// BREAKPOINT TOKENS
// ============================================================================

export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// ============================================================================
// Z-INDEX TOKENS
// ============================================================================

export const zIndex = {
  hide: -1,
  auto: 'auto',
  base: 0,
  docked: 10,
  dropdown: 1000,
  sticky: 1100,
  banner: 1200,
  overlay: 1300,
  modal: 1400,
  popover: 1500,
  skipLink: 1600,
  toast: 1700,
  tooltip: 1800,
} as const;

// ============================================================================
// TYPE EXPORTS
// ============================================================================

export type ColorScale = keyof typeof colors.navy;
export type SpacingKey = keyof typeof spacing;
export type TypographySize = keyof typeof typography.fontSize;
export type TypographyWeight = keyof typeof typography.fontWeight;
