/**
 * Design System Exports
 *
 * Central export point for all design tokens and utilities.
 */

// Design tokens
export * from './tokens';

// CSS files should be imported in your main CSS file:
// import './tokens.css' - Design tokens and CSS custom properties
// import './utilities.css' - Utility classes

// Re-export commonly used tokens for convenience
export { colors, spacing, typography, borderRadius, shadows, breakpoints, zIndex } from './tokens';

// Type exports
export type { ColorScale, SpacingKey, TypographySize, TypographyWeight } from './tokens';
