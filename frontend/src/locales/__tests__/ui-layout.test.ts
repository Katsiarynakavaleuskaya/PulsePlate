/**
 * UI Layout Tests for Localization
 *
 * Tests to ensure UI components can handle longer strings without layout issues.
 * Specifically tests Russian strings that can be up to 4x longer than English.
 */

import { describe, it, expect } from 'vitest';
import en from '../en.json';
import ru from '../ru.json';
import es from '../es.json';

// Test configuration constants
/** Maximum acceptable number of long strings across all locales - based on comprehensive localization dataset size */
const MAX_LONG_STRINGS = 150;
/** Number of longest strings to log for debugging - balances detail with log readability */
const TOP_LONG_STRINGS = 10;
/** Maximum length for critical UI strings (buttons, CTAs, titles) - based on mobile UI constraints */
const CRITICAL_MAX_LENGTH = 80;

describe('UI Layout Compatibility with Localized Strings', () => {
  const locales = { en, ru, es } as const;
  const languages = Object.keys(locales) as Array<keyof typeof locales>;

  describe('Critical UI String Length Validation', () => {
    it('should handle Russian strings without layout issues', () => {
      const criticalKeys = [
        'profile.legalSection',
        'profile.privacyPolicy',
        'profile.termsOfUse',
        'week.title',
        'health.permissionMessage',
        'mascot.plateHint',
        'mascot.homeWelcome',
        'mascot.progressGreat'
      ];

      for (const key of criticalKeys) {
        const enValue = getNestedValue(en, key);
        const ruValue = getNestedValue(ru, key);
        expect(enValue, `Missing EN key: ${key}`).toBeTruthy();
        expect(ruValue, `Missing RU key: ${key}`).toBeTruthy();

        if (enValue && ruValue) {
          const ratio = enValue.length === 0 ? 0 : ruValue.length / enValue.length;

          // Russian strings should not exceed 4x English length
          expect(ratio, `Russian string for '${key}' is ${ratio.toFixed(1)}x longer than English`).toBeLessThanOrEqual(4.0);

          // Store test results for potential debugging
          if (process.env.VITEST_VERBOSE_LOCALES === '1') {
            console.log(`UI Test: ${key} - EN: "${enValue}" (${enValue.length}) | RU: "${ruValue}" (${ruValue.length}) | Ratio: ${ratio.toFixed(1)}x`);
          }
        }
      }
    });

    it('should validate button and CTA text lengths', () => {
      const buttonKeys = [
        'vip.cta',
        'paywall.cta',
        'common.ok',
        'common.cancel',
        'week.refresh',
        'health.request'
      ];

      for (const key of buttonKeys) {
        const enValue = getNestedValue(en, key);
        const ruValue = getNestedValue(ru, key);
        expect(enValue, `Missing EN key: ${key}`).toBeTruthy();
        expect(ruValue, `Missing RU key: ${key}`).toBeTruthy();

        if (enValue && ruValue) {
          // Button text should be reasonable length for mobile UI
          expect(ruValue.length, `Russian button text for '${key}' is too long: "${ruValue}"`).toBeLessThanOrEqual(50);
          expect(enValue.length, `English button text for '${key}' is too long: "${enValue}"`).toBeLessThanOrEqual(50);
        }
      }
    });

    it('should validate accessibility label lengths', () => {
      const accessibilityKeys = [
        'vip.badgeAria',
        'vip.gatedAria',
        'profile.screenAccessibilityLabel',
        'accessibility.homeScreen',
        'week.chartAccessibility'
      ];

      for (const key of accessibilityKeys) {
        const enValue = getNestedValue(en, key);
        const ruValue = getNestedValue(ru, key);
        expect(enValue, `Missing EN key: ${key}`).toBeTruthy();
        expect(ruValue, `Missing RU key: ${key}`).toBeTruthy();

        if (enValue && ruValue) {
          // Accessibility labels should be concise but descriptive
          expect(ruValue.length, `Russian accessibility label for '${key}' is too long: "${ruValue}"`).toBeLessThanOrEqual(100);
          expect(enValue.length, `English accessibility label for '${key}' is too long: "${enValue}"`).toBeLessThanOrEqual(100);
        }
      }
    });
  });

  describe('Cross-Platform Consistency', () => {
    it('should maintain consistent terminology across all languages', () => {
      const terminologyChecks = [
        { key: 'vip.title', expectedTerms: ['VIP'] },
        { key: 'paywall.title', expectedTerms: ['VIP'] },
        { key: 'units.kcal', expectedTerms: ['kcal', 'ккал'] },
        { key: 'abbreviations.protein', expectedTerms: ['P', 'Б'] }
      ];

      for (const check of terminologyChecks) {
        for (const lang of languages) {
          const value = getNestedValue(locales[lang], check.key);
          if (value) {
            const hasExpectedTerm = check.expectedTerms.some(term =>
              value.toLowerCase().includes(term.toLowerCase())
            );
            expect(hasExpectedTerm, `Terminology check failed for '${check.key}' in ${lang}: "${value}"`).toBe(true);
          }
        }
      }
    });
  });

  describe('Layout Stress Testing', () => {
    it('should identify potentially problematic long strings', () => {
      const longStrings: Array<{key: string, value: string, length: number, language: string}> = [];

      const findLongStrings = (obj: unknown, path = '', lang: string) => {
        if (typeof obj === 'string') {
          if (obj.length > 30) { // Flag strings longer than 30 characters
            longStrings.push({ key: path, value: obj, length: obj.length, language: lang });
          }
        } else if (typeof obj === 'object' && obj !== null) {
          for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
            findLongStrings(value, path ? `${path}.${key}` : key, lang);
          }
        }
      };

      for (const lang of languages) {
        findLongStrings(locales[lang], '', lang);
      }

      // Validate that we have reasonable number of long strings
      // Note: MAX_LONG_STRINGS (150) long strings is acceptable for a comprehensive localization
      expect(longStrings.length, `Too many long strings detected (${longStrings.length}) - consider shortening translations (max: ${MAX_LONG_STRINGS})`).toBeLessThan(MAX_LONG_STRINGS);

      // Log for debugging only in development
      if (longStrings.length > 0 && process.env.VITEST_VERBOSE_LOCALES === '1') {
        console.log('\n=== Long Strings Requiring UI Review ===');
        longStrings
          .sort((a, b) => b.length - a.length)
          .slice(0, TOP_LONG_STRINGS) // Top longest strings for debugging
          .forEach(item => {
            console.log(`${item.language.toUpperCase()}: ${item.key} (${item.length} chars) - "${item.value}"`);
          });
      }

      // Assert that strings in critical UI areas don't exceed reasonable limits
      const criticalAreas = longStrings.filter(item =>
        item.key.includes('button') ||
        item.key.includes('cta') ||
        item.key.includes('title')
      );
      const excessiveStrings = criticalAreas.filter(item => item.length > CRITICAL_MAX_LENGTH);
      expect(excessiveStrings, `Found ${excessiveStrings.length} excessively long strings in critical UI areas (max: ${CRITICAL_MAX_LENGTH} chars)`).toHaveLength(0);
    });
  });

  describe('Localization placeholder invariants', () => {
    it('week.progressAccessibilityLine has identical placeholder sets across locales', () => {
      const keys = (s: string) => {
        return new Set(Array.from(s.matchAll(/{(\w+)}/g), m => m[1]));
      };
      const enSet = keys(en.week.progressAccessibilityLine);
      const ruSet = keys(ru.week.progressAccessibilityLine);
      const esSet = keys(es.week.progressAccessibilityLine);
      expect(ruSet).toEqual(enSet);
      expect(esSet).toEqual(enSet);
    });
  });
});

/**
 * Helper function to get nested object values by dot notation with type safety
 */
function getNestedValue(obj: Record<string, unknown>, path: string): string | undefined {
  const value = path.split('.').reduce<unknown>((current, key) => {
    if (current && typeof current === 'object' && current !== null) {
      return (current as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);

  // Type guard to ensure we return only strings
  return typeof value === 'string' ? value : undefined;
}
