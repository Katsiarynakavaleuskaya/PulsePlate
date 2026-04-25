/**
 * TabBar and app-shell helper functions.
 *
 * Utility functions for shared shell anatomy and TabBar component logic.
 */

const APP_SHELL_BASE_CLASS =
  'min-h-dvh bg-[var(--pp-navy)] text-[var(--pp-text)]';
const APP_SHELL_WITH_TAB_BAR_CLASS = 'pb-[var(--spacing-touch-large)]';
const TAB_BAR_BASE_CLASS =
  'fixed bottom-0 inset-x-0 grid border-t border-[color:var(--color-border)] bg-[var(--pp-navy)] shadow-[var(--shadow-lg)]';
const TAB_ITEM_BASE_CLASS =
  'relative py-3 text-center transition-all duration-200';

export const DISABLED_TAB_FEEDBACK_MS = 300;
export const AVAILABLE_TAB_CLASS =
  `${TAB_ITEM_BASE_CLASS} hover:scale-105 text-[var(--color-text-muted)]`;
export const ACTIVE_TAB_CLASS =
  `${TAB_ITEM_BASE_CLASS} hover:scale-105 text-[var(--color-primary)] font-medium`;
export const DISABLED_TAB_BASE_CLASS =
  `${TAB_ITEM_BASE_CLASS} cursor-not-allowed`;
export const DISABLED_TAB_LABEL_CLASS =
  'text-[var(--color-text-muted)] opacity-30 font-medium relative z-10';
export const DISABLED_TAB_OVERLAY_CLASS =
  'absolute inset-0 flex items-center justify-center bg-[var(--pp-navy)]/80 rounded-[var(--radius-lg)] backdrop-blur-sm';
export const DISABLED_TAB_ICON_CLASS =
  'h-4 w-4 text-[var(--color-text-muted)] opacity-70';
export const DISABLED_TAB_FEEDBACK_CLASS =
  'absolute inset-0 bg-[var(--color-primary)]/20 rounded-[var(--radius-lg)] animate-pulse';
export const ACTIVE_INDICATOR_CLASS =
  'absolute top-0 left-1/2 h-0.5 w-8 -translate-x-1/2 transform rounded-full bg-[var(--color-primary)]';

export const getAppShellClass = (withTabBar: boolean): string => {
  return withTabBar
    ? `${APP_SHELL_BASE_CLASS} ${APP_SHELL_WITH_TAB_BAR_CLASS}`
    : APP_SHELL_BASE_CLASS;
};

/**
 * Maps tab count to Tailwind CSS grid classes
 * @param count Number of visible tabs (1-6)
 * @returns Tailwind grid class string
 */
export const getGridColsClass = (count: number): string => {
  switch (count) {
    case 1: return 'grid-cols-1';
    case 2: return 'grid-cols-2';
    case 3: return 'grid-cols-3';
    case 4: return 'grid-cols-4';
    case 5: return 'grid-cols-5';
    case 6: return 'grid-cols-6';
    default: return 'grid-cols-3';
  }
};

export const getTabBarClass = (visibleTabsCount: number): string => {
  return `${TAB_BAR_BASE_CLASS} ${getGridColsClass(visibleTabsCount)}`;
};
