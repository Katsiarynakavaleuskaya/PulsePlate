import { describe, it, expect } from 'vitest';
import en from '../en.json';
import ru from '../ru.json';
import es from '../es.json';

describe('WHO Targets i18n', () => {
  const locales = { en, ru, es };

  describe('Structure Validation', () => {
    it('should have whoTargets section in all locales', () => {
      Object.entries(locales).forEach(([locale, data]) => {
        expect(data.whoTargets, `Missing whoTargets in ${locale}`).toBeDefined();
      });
    });

    it('should have consistent whoTargets structure across all locales', () => {
      const enKeys = Object.keys(en.whoTargets);
      const ruKeys = Object.keys(ru.whoTargets);
      const esKeys = Object.keys(es.whoTargets);

      expect(ruKeys).toEqual(enKeys);
      expect(esKeys).toEqual(enKeys);
    });

    it('should have all required subsections', () => {
      const requiredSections = [
        'calories',
        'macros',
        'hydration',
        'micros',
        'activity',
        'warnings',
        'empty',
        'error'
      ];

      Object.entries(locales).forEach(([locale, data]) => {
        requiredSections.forEach(section => {
          expect(
            (data.whoTargets as any)[section],
            `Missing ${section} section in ${locale}`
          ).toBeDefined();
        });
      });
    });
  });

  describe('Content Validation', () => {
    it('should have non-empty values for all keys', () => {
      Object.entries(locales).forEach(([locale, data]) => {
        const checkObject = (obj: any, path: string = '') => {
          Object.entries(obj).forEach(([key, value]) => {
            const currentPath = path ? `${path}.${key}` : key;

            if (typeof value === 'object' && value !== null) {
              checkObject(value, currentPath);
            } else {
              expect(
                value,
                `Empty value at ${currentPath} in ${locale}`
              ).toBeTruthy();
              expect(
                typeof value,
                `Non-string value at ${currentPath} in ${locale}`
              ).toBe('string');
            }
          });
        };

        checkObject(data.whoTargets);
      });
    });

    it('should have proper macro labels', () => {
      const macroKeys = ['protein', 'carbs', 'fat', 'fiber'];

      Object.entries(locales).forEach(([locale, data]) => {
        macroKeys.forEach(key => {
          expect(
            (data.whoTargets.macros as any)[key],
            `Missing macro key ${key} in ${locale}`
          ).toBeDefined();
        });
      });
    });

    it('should have proper activity labels', () => {
      const activityKeys = ['moderateAerobic', 'strength', 'steps'];

      Object.entries(locales).forEach(([locale, data]) => {
        activityKeys.forEach(key => {
          expect(
            (data.whoTargets.activity as any)[key],
            `Missing activity key ${key} in ${locale}`
          ).toBeDefined();
        });
      });
    });

    it('should have proper activity units', () => {
      const unitKeys = ['minutes', 'sessions', 'stepsUnit'];

      Object.entries(locales).forEach(([locale, data]) => {
        unitKeys.forEach(key => {
          expect(
            (data.whoTargets.activity as any)[key],
            `Missing activity unit ${key} in ${locale}`
          ).toBeDefined();
        });
      });
    });

    it('should have proper micronutrient labels', () => {
      const microKeys = ['iron_mg', 'calcium_mg'];

      Object.entries(locales).forEach(([locale, data]) => {
        microKeys.forEach(key => {
          expect(
            (data.whoTargets.micros as any)[key],
            `Missing micronutrient key ${key} in ${locale}`
          ).toBeDefined();
        });
      });
    });
  });

  describe('Translation Quality', () => {
    it('should use appropriate nutrition terminology', () => {
      // Check that Russian uses proper nutrition terms
      expect(ru.whoTargets.macros.protein).toContain('Белк');
      expect(ru.whoTargets.macros.carbs).toContain('Углевод');
      expect(ru.whoTargets.macros.fat).toContain('Жир');

      // Check that Spanish uses proper nutrition terms
      expect(es.whoTargets.macros.protein).toContain('Proteína');
      expect(es.whoTargets.macros.carbs).toContain('Carbohidrato');
      expect(es.whoTargets.macros.fat).toContain('Grasa');
    });

    it('should have consistent terminology across sections', () => {
      // Check that "calories" terminology is consistent
      expect(en.whoTargets.calories.title).toContain('Calories');
      expect(ru.whoTargets.calories.title).toContain('калори');
      expect(es.whoTargets.calories.title).toContain('Caloría');
    });

    it('should have appropriate text lengths for UI', () => {
      Object.entries(locales).forEach(([locale, data]) => {
        // Check that titles are not too long
        expect(data.whoTargets.calories.title.length).toBeLessThan(30);
        expect(data.whoTargets.macros.title.length).toBeLessThan(30);
        expect(data.whoTargets.hydration.title.length).toBeLessThan(30);
        expect(data.whoTargets.activity.title.length).toBeLessThan(30);

        // Check that descriptions are reasonable length
        expect(data.whoTargets.calories.description.length).toBeLessThan(100);
        expect(data.whoTargets.hydration.description.length).toBeLessThan(100);
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper accessibility labels', () => {
      Object.entries(locales).forEach(([locale, data]) => {
        expect(
          data.whoTargets.empty.iconLabel,
          `Missing icon label in ${locale}`
        ).toBeDefined();
        expect(
          data.whoTargets.empty.iconLabel.length,
          `Icon label too long in ${locale}`
        ).toBeLessThan(50);
      });
    });

    it('should have clear error messages', () => {
      Object.entries(locales).forEach(([locale, data]) => {
        expect(
          data.whoTargets.error.title,
          `Missing error title in ${locale}`
        ).toBeDefined();
        expect(
          data.whoTargets.error.retry,
          `Missing retry button text in ${locale}`
        ).toBeDefined();
      });
    });
  });
});
