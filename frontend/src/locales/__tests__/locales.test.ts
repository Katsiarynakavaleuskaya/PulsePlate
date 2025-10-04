/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

// Supported locales
const SUPPORTED_LOCALES = ['en', 'es', 'ru'] as const;
type SupportedLocale = typeof SUPPORTED_LOCALES[number];

// Test data for placeholder heuristics validation
interface PlaceholderTestCase {
  locale: SupportedLocale;
  key: string;
  value: string;
  shouldFail: boolean;
  reason?: string;
}

// Placeholder validation patterns - tightened to avoid false positives
const PLACEHOLDER_PATTERNS = [
  // Word-boundary test to avoid matching "testosterona", "intestino", etc.
  /\btest\b/i,
  /\bplaceholder\b/i,
  /\btodo\b/i,
  /\bfixme\b/i,
  /\bxxx\b/i,
  /\btbd\b/i,
];

/**
 * Validates that locale files contain no problematic placeholders
 */
function validateNoPlaceholders(locale: SupportedLocale, data: any, keyPath = ''): PlaceholderTestCase[] {
  const issues: PlaceholderTestCase[] = [];

  function checkValue(value: any, currentPath: string) {
    if (typeof value === 'string') {
      for (const pattern of PLACEHOLDER_PATTERNS) {
        if (pattern.test(value)) {
          issues.push({
            locale,
            key: currentPath,
            value,
            shouldFail: true,
            reason: `Contains placeholder pattern: ${pattern.source}`
          });
        }
      }
    } else if (typeof value === 'object' && value !== null) {
      for (const [key, val] of Object.entries(value)) {
        checkValue(val, currentPath ? `${currentPath}.${key}` : key);
      }
    }
  }

  checkValue(data, keyPath);
  return issues;
}

/**
 * Loads and parses a locale JSON file
 */
function loadLocaleFile(locale: SupportedLocale): any {
  const filePath = path.join(__dirname, '..', `${locale}.json`);
  const content = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(content);
}

describe('Locale Files Validation', () => {
  describe('Structural Validation', () => {
    it('should load all supported locale files', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        expect(() => loadLocaleFile(locale)).not.toThrow();
      });
    });

    it('should have consistent top-level structure across locales', () => {
      const enData = loadLocaleFile('en');

      SUPPORTED_LOCALES.forEach(locale => {
        if (locale === 'en') return; // Skip self-comparison

        const localeData = loadLocaleFile(locale);
        const enKeys = Object.keys(enData);
        const localeKeys = Object.keys(localeData);

        // Check that all top-level keys exist
        enKeys.forEach(key => {
          expect(localeKeys).toContain(key);
        });
      });
    });

    it('should have valid JSON structure', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);
        expect(typeof data).toBe('object');
        expect(data).not.toBeNull();
      });
    });

    it('should not contain undefined or null values', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);

        function checkForNulls(obj: any, path = ''): string[] {
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
        }

        const nullPaths = checkForNulls(data);
        expect(nullPaths).toHaveLength(0);
      });
    });

    it('should have consistent nested structure for paywall section', () => {
      const enPaywall = loadLocaleFile('en').paywall;

      SUPPORTED_LOCALES.forEach(locale => {
        const localePaywall = loadLocaleFile(locale).paywall;

        function compareStructure(enObj: any, localeObj: any, path = ''): string[] {
          const issues: string[] = [];

          if (typeof enObj !== typeof localeObj) {
            issues.push(`Type mismatch at ${path}: EN=${typeof enObj}, ${locale}=${typeof localeObj}`);
            return issues;
          }

          if (typeof enObj === 'object' && enObj !== null) {
            const enKeys = Object.keys(enObj);
            const localeKeys = Object.keys(localeObj);

            enKeys.forEach(key => {
              if (!localeKeys.includes(key)) {
                issues.push(`Missing key '${key}' in ${locale} at ${path}`);
              } else {
                issues.push(...compareStructure(enObj[key], localeObj[key], path ? `${path}.${key}` : key));
              }
            });
          }

          return issues;
        }

        const structureIssues = compareStructure(enPaywall, localePaywall, 'paywall');
        expect(structureIssues).toHaveLength(0);
      });
    });

    it('should have all string values be non-empty', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);

        function checkEmptyStrings(obj: any, path = ''): string[] {
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
        }

        const emptyPaths = checkEmptyStrings(data);
        expect(emptyPaths).toHaveLength(0);
      });
    });

    it('should not contain HTML tags', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);

        function checkForHtml(obj: any, path = ''): string[] {
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
        }

        const htmlPaths = checkForHtml(data);
        expect(htmlPaths).toHaveLength(0);
      });
    });
  });

  describe('Content Validation', () => {
    it('should not contain placeholder patterns', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);
        const placeholderIssues = validateNoPlaceholders(locale, data);

        // Filter out issues that should actually fail
        const actualFailures = placeholderIssues.filter(issue => issue.shouldFail);

        if (actualFailures.length > 0) {
          console.log('Placeholder issues found:', actualFailures);
        }

        expect(actualFailures).toHaveLength(0);
      });
    });

    it('should have reasonable string lengths for UI components', () => {
      const MAX_TITLE_LENGTH = 50;
      const MAX_SUBTITLE_LENGTH = 100;
      const MAX_BUTTON_LENGTH = 30;

      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);

        // Check paywall title length
        if (data.paywall?.title) {
          expect(data.paywall.title.length).toBeLessThanOrEqual(MAX_TITLE_LENGTH);
        }

        // Check paywall subtitle length
        if (data.paywall?.subtitle) {
          expect(data.paywall.subtitle.length).toBeLessThanOrEqual(MAX_SUBTITLE_LENGTH);
        }

        // Check button text lengths
        if (data.paywall?.cta) {
          expect(data.paywall.cta.length).toBeLessThanOrEqual(MAX_BUTTON_LENGTH);
        }

        if (data.common?.cancel) {
          expect(data.common.cancel.length).toBeLessThanOrEqual(MAX_BUTTON_LENGTH);
        }
      });
    });

    it('should contain only valid Unicode characters', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);

        function checkUnicode(obj: any, path = ''): string[] {
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
        }

        const unicodeIssues = checkUnicode(data);
        expect(unicodeIssues).toHaveLength(0);
      });
    });

    it('should have consistent terminology across locales', () => {
      // This is a basic check - in a real implementation you'd want more sophisticated
      // terminology consistency validation
      const enData = loadLocaleFile('en');

      SUPPORTED_LOCALES.forEach(locale => {
        if (locale === 'en') return;

        const localeData = loadLocaleFile(locale);

        // Check that key sections exist
        expect(localeData.paywall).toBeDefined();
        expect(localeData.common).toBeDefined();
      });
    });

    it('should not contain duplicate values within the same locale', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);
        const allValues: string[] = [];

        function collectValues(obj: any) {
          if (typeof obj === 'string') {
            allValues.push(obj);
          } else if (typeof obj === 'object' && obj !== null) {
            Object.values(obj).forEach(collectValues);
          }
        }

        collectValues(data);

        const duplicates = allValues.filter((value, index) => allValues.indexOf(value) !== index);
        const uniqueDuplicates = [...new Set(duplicates)];

        // Allow some common words that might legitimately be duplicated
        const allowedDuplicates = ['OK', 'and', 'or', 'the', 'to', 'of', 'in', 'on', 'at'];

        const problematicDuplicates = uniqueDuplicates.filter(dup => !allowedDuplicates.includes(dup));

        expect(problematicDuplicates).toHaveLength(0);
      });
    });

    it('should follow consistent capitalization patterns', () => {
      SUPPORTED_LOCALES.forEach(locale => {
        const data = loadLocaleFile(locale);

        // Check that titles are properly capitalized
        if (data.paywall?.title) {
          // First letter should be uppercase for titles
          expect(data.paywall.title[0]).toMatch(/[A-ZА-Я]/);
        }

        // Check that button text follows consistent patterns
        if (data.paywall?.cta) {
          // CTA buttons should start with uppercase
          expect(data.paywall.cta[0]).toMatch(/[A-ZА-Я]/);
        }
      });
    });
  });
});
