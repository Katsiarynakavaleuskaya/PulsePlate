import { describe, it, expect } from 'vitest';
import {
  ACTIVE_TAB_CLASS,
  AVAILABLE_TAB_CLASS,
  DISABLED_TAB_BASE_CLASS,
  getAppShellClass,
  getGridColsClass,
  getTabBarClass,
} from '../TabBar.helpers';

describe('TabBar.helpers', () => {
  describe('getGridColsClass', () => {
    const testCases: [number, string][] = [
      [1, 'grid-cols-1'],
      [2, 'grid-cols-2'],
      [3, 'grid-cols-3'],
      [4, 'grid-cols-4'],
      [5, 'grid-cols-5'],
      [6, 'grid-cols-6'],
      [0, 'grid-cols-3'],    // default/fallback
      [10, 'grid-cols-3'],   // default/fallback
      [-1, 'grid-cols-3'],   // default/fallback
    ];

    testCases.forEach(([input, expected]) => {
      it(`maps ${input} -> ${expected}`, () => {
        expect(getGridColsClass(input)).toBe(expected);
      });
    });
  });

  describe('getAppShellClass', () => {
    it('uses runtime token classes and reserves tab bar space only when needed', () => {
      expect(getAppShellClass(true)).toContain('bg-[var(--pp-navy)]');
      expect(getAppShellClass(true)).toContain('text-[var(--pp-text)]');
      expect(getAppShellClass(true)).toContain('pb-[var(--spacing-touch-large)]');
      expect(getAppShellClass(false)).not.toContain('pb-[var(--spacing-touch-large)]');
    });
  });

  describe('getTabBarClass', () => {
    it('composes navigation/tab-bar class with runtime token classes', () => {
      const className = getTabBarClass(4);

      expect(className).toContain('grid-cols-4');
      expect(className).toContain('bg-[var(--pp-navy)]');
      expect(className).toContain('border-[color:var(--color-border)]');
    });
  });

  describe('tab item state classes', () => {
    it('uses runtime token classes for active available and disabled states', () => {
      expect(ACTIVE_TAB_CLASS).toContain('text-[var(--color-primary)]');
      expect(AVAILABLE_TAB_CLASS).toContain('text-[var(--color-text-muted)]');
      expect(DISABLED_TAB_BASE_CLASS).toContain('cursor-not-allowed');
    });
  });
});
