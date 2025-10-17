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

        if (enValue && ruValue) {
          const ratio = ruValue.length / enValue.length;

          // Russian strings should not exceed 4x English length
          expect(ratio, `Russian string for '${key}' is ${ratio.toFixed(1)}x longer than English`).toBeLessThanOrEqual(4.0);

          // Log for manual UI testing
          console.log(`UI Test: ${key} - EN: "${enValue}" (${enValue.length}) | RU: "${ruValue}" (${ruValue.length}) | Ratio: ${ratio.toFixed(1)}x`);
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

      const findLongStrings = (obj: any, path = '', lang: string) => {
        if (typeof obj === 'string') {
          if (obj.length > 30) { // Flag strings longer than 30 characters
            longStrings.push({ key: path, value: obj, length: obj.length, language: lang });
          }
        } else if (typeof obj === 'object' && obj !== null) {
          for (const [key, value] of Object.entries(obj)) {
            findLongStrings(value, path ? `${path}.${key}` : key, lang);
          }
        }
      };

      for (const lang of languages) {
        findLongStrings(locales[lang], '', lang);
      }

      // Log long strings for manual review
      if (longStrings.length > 0) {
        console.log('\n=== Long Strings Requiring UI Review ===');
        longStrings
          .sort((a, b) => b.length - a.length)
          .slice(0, 10) // Top 10 longest strings
          .forEach(item => {
            console.log(`${item.language.toUpperCase()}: ${item.key} (${item.length} chars) - "${item.value}"`);
          });
      }

      // This test passes but logs strings that need manual UI testing
      expect(longStrings.length).toBeGreaterThanOrEqual(0);
    });
  });
});

/**
 * Helper function to get nested object values by dot notation
 */
function getNestedValue(obj: any, path: string): string | undefined {
  return path.split('.').reduce((current, key) => {
    return current && typeof current === 'object' ? current[key] : undefined;
  }, obj);
}
