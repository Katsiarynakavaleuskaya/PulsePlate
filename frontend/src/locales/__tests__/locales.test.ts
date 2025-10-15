/* @vitest-environment jsdom */
import { describe, it, expect } from 'vitest';
import en from '../en.json';
import ru from '../ru.json';
import es from '../es.json';
import {
  collectKeyPaths,
  checkLengths,
  getMaxLength,
  MAX_ALLOWED_DUPLICATES,
  STRING_LENGTH_LIMITS,
  TestLogger
} from '../../test-utils/locales';

// Test constants imported from test-utils

describe('Locale JSON Structure and Content', () => {
  const locales = { en, ru, es };
  const languages = Object.keys(locales);

  describe('Structural Validation', () => {
    it('should have consistent keys across all locales', () => {
      const enKeyPaths = collectKeyPaths(en).sort();

      for (const lang of languages) {
        const keyPaths = collectKeyPaths(locales[lang]).sort();
        expect(keyPaths).toEqual(enKeyPaths);
      }
    });

    it('should not contain null or undefined values', () => {
      const checkForNulls = (obj: any, path = ''): string[] => {
        const issues: string[] = [];

        if (obj === null) {
          issues.push(path);
        } else if (obj === undefined) {
          issues.push(path);
        } else if (typeof obj === 'object') {
          for (const [key, value] of Object.entries(obj)) {
            issues.push(...checkForNulls(value, path ? `${path}.${key}` : key));
          }
        }

        return issues;
      };

      for (const lang of languages) {
        const issues = checkForNulls(locales[lang]);
        expect(issues).toHaveLength(0);
      }
    });

    it('should not contain empty strings', () => {
      const checkEmptyStrings = (obj: any, path = ''): string[] => {
        const issues: string[] = [];

        if (typeof obj === 'string') {
          if (obj.trim().length === 0) {
            issues.push(path);
          }
        } else if (typeof obj === 'object' && obj !== null) {
          for (const [key, value] of Object.entries(obj)) {
            issues.push(...checkEmptyStrings(value, path ? `${path}.${key}` : key));
          }
        }

        return issues;
      };

      for (const lang of languages) {
        const issues = checkEmptyStrings(locales[lang]);
        expect(issues).toHaveLength(0);
      }
    });

    it('should not contain HTML tags', () => {
      const checkForHtml = (obj: any, path = ''): string[] => {
        const issues: string[] = [];

        if (typeof obj === 'string') {
          if (/<[^>]*>/.test(obj)) {
            issues.push(path);
          }
        } else if (typeof obj === 'object' && obj !== null) {
          for (const [key, value] of Object.entries(obj)) {
            issues.push(...checkForHtml(value, path ? `${path}.${key}` : key));
          }
        }

        return issues;
      };

      for (const lang of languages) {
        const issues = checkForHtml(locales[lang]);
        expect(issues).toHaveLength(0);
      }
    });

    it('should contain only valid Unicode characters', () => {
      const checkUnicode = (obj: any, path = ''): string[] => {
        const issues: string[] = [];

        if (typeof obj === 'string') {
          // Check for control characters (except common whitespace)
          for (let i = 0; i < obj.length; i++) {
            const code = obj.charCodeAt(i);
            if (code < 32 && code !== 9 && code !== 10 && code !== 13) {
              issues.push(`${path}: Invalid control character at position ${i} (U+${code.toString(16).toUpperCase()})`);
            }
          }
        } else if (typeof obj === 'object' && obj !== null) {
          for (const [key, value] of Object.entries(obj)) {
            issues.push(...checkUnicode(value, path ? `${path}.${key}` : key));
          }
        }

        return issues;
      };

      for (const lang of languages) {
        const issues = checkUnicode(locales[lang]);
        expect(issues).toHaveLength(0);
      }
    });
  });

  describe('Content Validation', () => {
    it('should not contain placeholder patterns', () => {
      const PLACEHOLDER_PATTERNS = [
        /\btest\b/i,
        /\bplaceholder\b/i,
        /\btodo\b/i,
        /\bfixme\b/i,
        /\bxxx\b/i,
        /\btbd\b/i
      ];

      for (const lang of languages) {
        const issues: Array<{key: string, value: string, pattern: string}> = [];

        const checkValue = (value: any, currentPath: string) => {
          if (typeof value === 'string') {
            // Skip legitimate placeholder translations (keys ending with .placeholder)
            if (currentPath.endsWith('.placeholder')) {
              return;
            }

            for (const pattern of PLACEHOLDER_PATTERNS) {
              if (pattern.test(value)) {
                issues.push({
                  key: currentPath,
                  value,
                  pattern: pattern.source
                });
              }
            }
          } else if (typeof value === 'object' && value !== null) {
            for (const [key, val] of Object.entries(value)) {
              checkValue(val, currentPath ? `${currentPath}.${key}` : key);
            }
          }
        };

        checkValue(locales[lang], '');
        expect(issues).toHaveLength(0);
      }
    });

    it('should have reasonable string lengths', () => {
      for (const lang of languages) {
        const issues = checkLengths(locales[lang]);
        expect(issues).toHaveLength(0);
      }
    });

    // Boundary tests for string length validation
    describe('String length validation', () => {
      test.each([
        { path: 'description', length: STRING_LENGTH_LIMITS.extended },
        { path: 'legal', length: STRING_LENGTH_LIMITS.extended },
        { path: 'disclaimer', length: STRING_LENGTH_LIMITS.extended },
        { path: 'title', length: STRING_LENGTH_LIMITS.default },
        { path: 'name', length: STRING_LENGTH_LIMITS.default },
      ])('should allow strings exactly at the max length for $path', ({ path, length }) => {
        const obj = { [path]: 'a'.repeat(length) };
        const issues = checkLengths(obj, '');
        expect(issues).toHaveLength(0);
      });

      test.each([
        { path: 'description', length: STRING_LENGTH_LIMITS.extended + 1 },
        { path: 'legal', length: STRING_LENGTH_LIMITS.extended + 1 },
        { path: 'disclaimer', length: STRING_LENGTH_LIMITS.extended + 1 },
        { path: 'title', length: STRING_LENGTH_LIMITS.default + 1 },
        { path: 'name', length: STRING_LENGTH_LIMITS.default + 1 },
      ])('should report strings just above the max length for $path', ({ path, length }) => {
        const obj = { [path]: 'a'.repeat(length) };
        const issues = checkLengths(obj, '');
        expect(issues.length).toBeGreaterThan(0);
        expect(issues[0]).toMatch(/Invalid length.*max:/);
      });
    });

    it('should not have problematic duplicate values', () => {
      // Collect all string values from the locale
      const allValues: string[] = [];
      const collectValues = (obj: any) => {
        if (typeof obj === 'string') {
          allValues.push(obj);
        } else if (typeof obj === 'object' && obj !== null) {
          Object.values(obj).forEach(collectValues);
        }
      };

      for (const lang of languages) {
        allValues.length = 0; // Reset array
        collectValues(locales[lang]);

        // Find duplicates
        const valueCount: Record<string, number> = {};
        allValues.forEach(value => {
          valueCount[value] = (valueCount[value] || 0) + 1;
        });

        const duplicates = Object.entries(valueCount)
          .filter(([, count]) => count > 1)
          .map(([value]) => value);

        // Allow some common words that are legitimately duplicated
        const allowedDuplicates = ['OK', 'Error', '≈', 'kcal'];

        const problematicDuplicates = duplicates.filter(dup => !allowedDuplicates.includes(dup));

        // Log duplicates for visibility even if test passes
        const logger = new TestLogger();
        if (problematicDuplicates.length > 0) {
          logger.warn(`[${lang}] Found ${problematicDuplicates.length} duplicate values:`,
            problematicDuplicates.slice(0, 5).map(d => `"${d.substring(0, 50)}..."`).join(', '));
        }

        // Note: We expect some duplicates in locale files (like common UI elements)
        // This test ensures there are no unexpected problematic duplicates
        expect(problematicDuplicates.length).toBeLessThanOrEqual(MAX_ALLOWED_DUPLICATES);

        // Verify logging behavior
        if (problematicDuplicates.length > 0) {
          expect(logger.getLogs()).toHaveLength(1);
          expect(logger.getLogs()[0]).toContain(`[${lang}] Found ${problematicDuplicates.length} duplicate values`);
        } else {
          expect(logger.getLogs()).toHaveLength(0);
        }
      }
    });

    // Tests for duplicate logging and threshold
    describe('duplicate logging and threshold', () => {
      let logger: TestLogger;

      beforeEach(() => {
        logger = new TestLogger();
      });

      afterEach(() => {
        logger.clear();
      });

      it('logs a warning when problematic duplicates are detected', () => {
        const lang = 'fr';
        const duplicates = ['dup1', 'dup2', 'dup3'];
        const allowedDuplicates: string[] = ['dup1'];
        const problematicDuplicates = duplicates.filter(dup => !allowedDuplicates.includes(dup));

        if (problematicDuplicates.length > 0) {
          logger.warn(`[${lang}] Found ${problematicDuplicates.length} duplicate values:`,
            problematicDuplicates.slice(0, 5).map(d => `"${d.substring(0, 50)}..."`).join(', '));
        }

        expect(logger.getLogs()).toHaveLength(1);
        expect(logger.getLogs()[0]).toContain(`[${lang}] Found 2 duplicate values:`);
      });

      it('does not log a warning when no problematic duplicates are detected', () => {
        const lang = 'fr';
        const duplicates = ['dup1', 'dup2'];
        const allowedDuplicates: string[] = ['dup1', 'dup2'];
        const problematicDuplicates = duplicates.filter(dup => !allowedDuplicates.includes(dup));

        if (problematicDuplicates.length > 0) {
          logger.warn(`[${lang}] Found ${problematicDuplicates.length} duplicate values:`,
            problematicDuplicates.slice(0, 5).map(d => `"${d.substring(0, 50)}..."`).join(', '));
        }

        expect(logger.getLogs()).toHaveLength(0);
      });

      it('respects the configurable duplicate threshold', () => {
        // Arrange: create more duplicates than allowed
        const problematicDuplicates = Array(MAX_ALLOWED_DUPLICATES + 1).fill('dup');
        expect(problematicDuplicates.length).toBeGreaterThan(MAX_ALLOWED_DUPLICATES);

        // Act: simulate duplicate detection logic
        if (problematicDuplicates.length > MAX_ALLOWED_DUPLICATES) {
          logger.warn(`[testLang] Found ${problematicDuplicates.length} duplicate values:`,
            problematicDuplicates.slice(0, 5).map(d => `"${d.substring(0, 50)}..."`).join(', '));
        }

        // Assert: logger should have recorded a warning
        const logs = logger.getLogs();
        expect(logs.length).toBeGreaterThan(0);
        expect(logs[0]).toContain('Found');
        expect(logs[0]).toContain(`${problematicDuplicates.length} duplicate values`);
      });
    });
  });

  describe('Domain-Specific Validation', () => {
    describe('Paywall Section', () => {
      it('should have consistent paywall structure', () => {
        const paywallKeys = ['title', 'subtitle', 'cta', 'legal', 'before', 'after', 'items'];
        for (const lang of languages) {
          const { paywall } = locales[lang];
          expect(paywall).toBeDefined();
          expect(Object.keys(paywall).sort()).toEqual(paywallKeys.sort());
        }
      });

      it('should have proper before/after structure', () => {
        const sectionKeys = ['label', 'randomPlate', 'macrosOnly', 'manualShopping'];
        const afterKeys = ['label', 'personalPlate', 'microBalance', 'autoShoppingList'];
        for (const lang of languages) {
          const { paywall } = locales[lang];
          expect(Object.keys(paywall.before).sort()).toEqual(sectionKeys.sort());
          expect(Object.keys(paywall.after).sort()).toEqual(afterKeys.sort());
        }
      });

      it('should have consistent items structure', () => {
        const itemKeys = ['random_plate', 'macros_only', 'manual_shopping'];
        const afterItemKeys = ['personal_plate', 'micro_balance', 'auto_shopping_list'];
        for (const lang of languages) {
          const { items } = locales[lang].paywall;
          expect(items.before).toBeDefined();
          expect(items.after).toBeDefined();
          expect(Object.keys(items.before).sort()).toEqual(itemKeys.sort());
          expect(Object.keys(items.after).sort()).toEqual(afterItemKeys.sort());
        }
      });
    });

    describe('Spanish Translation Quality', () => {
      it('should use professional nutrition terminology', () => {
        const esPaywall = es.paywall;
        expect(esPaywall.after.personalPlate).toBe('Plan nutricional personal');
        expect(esPaywall.after.microBalance).toBe('Equilibrio nutricional');
        expect(esPaywall.before.macrosOnly).toBe('Solo macronutrientes');
      });

      it('should have proper subtitle', () => {
        expect(es.paywall.subtitle).toBe('Plan nutricional personal, equilibrio preciso, planificación semanal.');
      });

      it('should use correct legal text', () => {
        expect(es.paywall.legal).toBe('Suscripción con renovación automática. Cancela en Configuración.');
      });

      it('should have proper empty state', () => {
        expect(es.shoplist.empty).toBe('Lista vacía.');
      });
    });

    describe('Russian Translation Quality', () => {
      it('should use professional nutrition terminology', () => {
        const ruPaywall = ru.paywall;
        expect(ruPaywall.after.personalPlate).toBe('Персональный рацион');
        expect(ruPaywall.after.microBalance).toBe('Точный баланс');
        expect(ruPaywall.before.macrosOnly).toBe('Только макронутриенты');
      });

      it('should have proper subtitle', () => {
        expect(ru.paywall.subtitle).toBe('Персональный рацион, точный баланс, недельная программа.');
      });
    });
  });
});
